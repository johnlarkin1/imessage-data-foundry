"""Generation screen - progress display during conversation generation."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.widgets import Button, Label, ProgressBar, Static

from imessage_data_foundry.conversations.generator import (
    ConversationGenerator,
    GenerationProgress,
)
from imessage_data_foundry.db.builder import DatabaseBuilder
from imessage_data_foundry.llm.config import LLMConfig
from imessage_data_foundry.llm.manager import ProviderManager, ProviderNotAvailableError
from imessage_data_foundry.personas.models import ChatType, ConversationConfig
from imessage_data_foundry.personas.storage import PersonaStorage
from imessage_data_foundry.ui.screens.base import WizardScreen
from imessage_data_foundry.ui.state import Screen


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

    def body(self) -> ComposeResult:
        with Center(), Vertical(id="generation-content"):
            yield Label("Generating Conversation", id="gen-title", classes="section-label")
            yield Static("Initializing...", id="gen-phase")
            yield ProgressBar(total=100, show_eta=False, id="gen-progress")
            yield Static("", id="gen-stats")
            yield Static("", id="gen-result")

            with Center(id="gen-buttons"):
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
        phase_label = self.query_one("#gen-phase", Static)
        progress_bar = self.query_one("#gen-progress", ProgressBar)
        stats_label = self.query_one("#gen-stats", Static)
        result_label = self.query_one("#gen-result", Static)

        phase_label.update("Loading personas...")

        with PersonaStorage() as storage:
            all_personas = storage.list_all()

        selected_personas = [p for p in all_personas if p.id in self.state.selected_persona_ids]

        if len(selected_personas) < 2:
            phase_label.update("[red]Error: Not enough personas selected[/red]")
            self._finish_generation(success=False)
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

        phase_label.update("Connecting to LLM provider...")

        try:
            llm_config = LLMConfig()
            if self.state.provider_type:
                llm_config.default_provider = self.state.provider_type

            manager = ProviderManager(llm_config)
            generator = ConversationGenerator(manager, llm_config)

        except ProviderNotAvailableError as e:
            phase_label.update(f"[red]Provider error: {e}[/red]")
            self._finish_generation(success=False)
            return

        phase_label.update("Starting generation...")

        def on_progress(progress: GenerationProgress) -> None:
            self.call_from_thread(self._update_progress, progress)  # type: ignore[attr-defined]

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

            phase_label.update("[green]Generation complete![/green]")
            progress_bar.update(progress=100)

            stats_label.update(
                f"Messages: {len(result.messages)} | "
                f"Time: {result.generation_time_seconds:.1f}s | "
                f"Provider: {result.llm_provider_used}"
            )

            result_label.update(f"[bold]Output:[/bold] {self.state.output_path.absolute()}")

            self._finish_generation(success=True)

        except ProviderNotAvailableError as e:
            phase_label.update(f"[red]Provider not available: {e}[/red]")
            self._finish_generation(success=False)

        except Exception as e:
            phase_label.update(f"[red]Error: {e}[/red]")
            self._finish_generation(success=False)

    def _update_progress(self, progress: GenerationProgress) -> None:
        phase_label = self.query_one("#gen-phase", Static)
        progress_bar = self.query_one("#gen-progress", ProgressBar)
        stats_label = self.query_one("#gen-stats", Static)

        phase_map = {
            "generating": "Generating messages",
            "assigning_timestamps": "Assigning timestamps",
            "writing_database": "Writing to database",
        }
        phase_text = phase_map.get(progress.phase, progress.phase)
        phase_label.update(f"{phase_text}...")

        progress_bar.update(progress=progress.percent_complete)

        stats_label.update(
            f"Batch {progress.current_batch}/{progress.total_batches} | "
            f"{progress.generated_messages}/{progress.total_messages} messages"
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
                phase_label = self.query_one("#gen-phase", Static)
                phase_label.update("[yellow]Cancelled[/yellow]")
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
