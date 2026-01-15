"""Generation screen - progress display during conversation generation."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Label, ProgressBar, Static

from imessage_data_foundry.conversations.generator import (
    ConversationGenerator,
    GenerationProgress,
    TimestampedMessage,
)
from imessage_data_foundry.db.builder import DatabaseBuilder
from imessage_data_foundry.llm.config import LLMConfig
from imessage_data_foundry.llm.manager import ProviderManager, ProviderNotAvailableError
from imessage_data_foundry.personas.models import ChatType, ConversationConfig
from imessage_data_foundry.personas.storage import PersonaStorage
from imessage_data_foundry.ui.screens.base import WizardScreen
from imessage_data_foundry.ui.state import Screen
from imessage_data_foundry.ui.widgets import AnimatedSpinner


class GenerationScreen(WizardScreen):
    """Display generation progress and results."""

    SCREEN_ID = Screen.GENERATION

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._is_generating = False
        self._is_complete = False
        self._persona_names: dict[str, str] = {}

    def body(self) -> ComposeResult:
        with (
            VerticalScroll(id="gen-scroll"),
            Center(id="gen-center"),
            Vertical(id="generation-content"),
        ):
            yield Label("Generating Conversation", id="gen-title")
            yield AnimatedSpinner("Initializing...", id="gen-spinner")
            yield Static("[dim]Preparing generation...[/]", id="gen-phase")
            yield ProgressBar(total=100, show_eta=False, id="gen-progress")
            yield Static("[dim]Waiting to start...[/]", id="gen-stats")
            yield Static("", id="gen-result")
            yield Static("", id="gen-preview")

            with Horizontal(id="gen-buttons"):
                yield Button(
                    "Cancel",
                    id="cancel-btn",
                    variant="error",
                )
                yield Button(
                    "Generate Another",
                    id="another-btn",
                    variant="primary",
                    disabled=True,
                )
                yield Button(
                    "Done",
                    id="done-btn",
                    variant="success",
                    disabled=True,
                )

    def on_mount(self) -> None:
        self._start_generation()

    @work(exclusive=True)
    async def _start_generation(self) -> None:
        self._is_generating = True
        spinner = self.query_one("#gen-spinner", AnimatedSpinner)
        phase_label = self.query_one("#gen-phase", Static)
        progress_bar = self.query_one("#gen-progress", ProgressBar)
        stats_label = self.query_one("#gen-stats", Static)
        result_label = self.query_one("#gen-result", Static)

        spinner.update_text("Loading personas...")

        with PersonaStorage() as storage:
            all_personas = storage.list_all()

        selected_personas = [p for p in all_personas if p.id in self.state.selected_persona_ids]
        self._persona_names = {p.id: p.name for p in selected_personas}

        if len(selected_personas) < 2:
            self._show_error("Not enough personas selected")
            return

        config = ConversationConfig(
            participants=[p.id for p in selected_personas],
            chat_type=ChatType.DIRECT if len(selected_personas) == 2 else ChatType.GROUP,
            message_count_target=self.state.message_count,
            time_range_start=self.state.time_range_start,
            time_range_end=self.state.time_range_end,
            seed=self.state.seed,
            service=self.state.service,
        )

        spinner.update_text("Connecting to LLM provider...")

        try:
            llm_config = LLMConfig()
            if self.state.provider_type:
                llm_config.default_provider = self.state.provider_type

            manager = ProviderManager(llm_config)
            generator = ConversationGenerator(manager, llm_config)

        except ProviderNotAvailableError as e:
            self._show_error(f"Provider error: {e}")
            return

        spinner.update_text("Starting generation...")

        def on_progress(progress: GenerationProgress) -> None:
            self._update_progress(progress)

        try:
            self.state.output_path.parent.mkdir(parents=True, exist_ok=True)

            with DatabaseBuilder(
                self.state.output_path,
                version=self.state.macos_version,
            ) as builder:
                result = await generator.generate_to_database(
                    personas=selected_personas,
                    config=config,
                    builder=builder,
                    progress_callback=on_progress,
                )

            self.state.generation_result = result

            spinner.display = False
            phase_label.update("[#34C759 bold]Generation complete![/]")
            progress_bar.update(progress=100)

            stats_label.update(
                f"[dim]Messages:[/] {len(result.messages)}  |  "
                f"[dim]Time:[/] {result.generation_time_seconds:.1f}s  |  "
                f"[dim]Provider:[/] {result.llm_provider_used}"
            )

            result_label.update(
                f"[#34C759 bold]Output saved to:[/]\n{self.state.output_path.absolute()}"
            )
            result_label.add_class("success-result")

            self._show_preview(result.messages)

            self._finish_generation(success=True)

        except ProviderNotAvailableError as e:
            self._show_error(f"Provider not available: {e}")

        except Exception as e:
            self._show_error(str(e))

    def _show_error(self, message: str) -> None:
        try:
            spinner = self.query_one("#gen-spinner", AnimatedSpinner)
            phase_label = self.query_one("#gen-phase", Static)
            stats_label = self.query_one("#gen-stats", Static)
            result_label = self.query_one("#gen-result", Static)

            spinner.display = False
            phase_label.update("[#FF3B30 bold]Generation Failed[/]")
            stats_label.update("")
            result_label.update(f"[#FF3B30]{message}[/]")
            result_label.add_class("error-result")
        except Exception:
            pass
        self._finish_generation(success=False)

    def _show_preview(self, messages: list[TimestampedMessage]) -> None:
        try:
            preview_label = self.query_one("#gen-preview", Static)
            if not messages:
                return

            lines = ["[bold]Conversation Preview:[/]\n"]
            sample = messages[:10]

            for tm in sample:
                msg = tm.message
                name = self._persona_names.get(msg.sender_id, "Unknown")
                if msg.is_from_me:
                    lines.append(f"[#007AFF bold]{name}:[/] {msg.text}")
                else:
                    lines.append(f"[#8E8E93 bold]{name}:[/] {msg.text}")

            if len(messages) > 10:
                lines.append(f"\n[dim]... and {len(messages) - 10} more messages[/]")

            preview_label.update("\n".join(lines))
            preview_label.add_class("preview-box")
        except Exception:
            pass

    def _update_progress(self, progress: GenerationProgress) -> None:
        spinner = self.query_one("#gen-spinner", AnimatedSpinner)
        progress_bar = self.query_one("#gen-progress", ProgressBar)
        stats_label = self.query_one("#gen-stats", Static)

        phase_map = {
            "generating": "Generating messages",
            "assigning_timestamps": "Assigning timestamps",
            "writing_database": "Writing to database",
        }
        phase_text = phase_map.get(progress.phase, progress.phase)
        spinner.update_text(f"{phase_text}...")

        progress_bar.update(progress=progress.percent_complete)

        stats_label.update(
            f"[dim]Batch[/] {progress.current_batch}/{progress.total_batches}  |  "
            f"[dim]Messages[/] {progress.generated_messages}/{progress.total_messages}"
        )

    def _finish_generation(self, success: bool) -> None:
        self._is_generating = False
        self._is_complete = success

        cancel_btn = self.query_one("#cancel-btn", Button)
        another_btn = self.query_one("#another-btn", Button)
        done_btn = self.query_one("#done-btn", Button)

        cancel_btn.disabled = True
        another_btn.disabled = not success
        done_btn.disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            if self._is_generating:
                self.workers.cancel_all()
                spinner = self.query_one("#gen-spinner", AnimatedSpinner)
                phase_label = self.query_one("#gen-phase", Static)
                spinner.display = False
                phase_label.update("[#FF9500 bold]Cancelled[/]")
                self._finish_generation(success=False)

        elif event.button.id == "another-btn":
            self.state.reset_generation()
            self.app.pop_screen()

        elif event.button.id == "done-btn":
            self.app.exit()

    def action_back(self) -> None:
        if self._is_generating:
            self.notify("Cannot go back while generating", severity="warning")
            return
        self.app.pop_screen()
