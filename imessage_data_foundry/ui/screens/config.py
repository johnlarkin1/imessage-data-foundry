"""Configuration screen - macOS version, output path, LLM provider."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static

from imessage_data_foundry.db.schema.base import SchemaVersion
from imessage_data_foundry.db.version_detect import detect_schema_version
from imessage_data_foundry.llm.config import ProviderType
from imessage_data_foundry.llm.manager import ProviderManager
from imessage_data_foundry.ui.screens.base import NavigationBar, WizardScreen
from imessage_data_foundry.ui.state import Screen


class ConfigScreen(WizardScreen):
    """Configuration screen for setting up generation parameters."""

    SCREEN_ID = Screen.CONFIG

    def __init__(self) -> None:
        super().__init__()
        self._available_providers: list[tuple[ProviderType, str]] = []

    def body(self) -> ComposeResult:
        with Vertical(id="config-form"):
            with Container(classes="config-section"):
                yield Label("macOS Version", classes="config-section-title")
                detected = detect_schema_version()
                with RadioSet(id="version-select"):
                    yield RadioButton(
                        "Sequoia (macOS 15)",
                        id="version-sequoia",
                        value=detected == SchemaVersion.SEQUOIA,
                    )
                    yield RadioButton(
                        "Sonoma (macOS 14)",
                        id="version-sonoma",
                        value=detected == SchemaVersion.SONOMA,
                    )
                    yield RadioButton(
                        "Tahoe (macOS 26)",
                        id="version-tahoe",
                        value=detected == SchemaVersion.TAHOE,
                    )

            with Container(classes="config-section"):
                yield Label("Output Path", classes="config-section-title")
                yield Input(
                    str(self.state.output_path),
                    id="output-path",
                    placeholder="./output/chat.db",
                )
                yield Label("Database will be created at this location", classes="hint")

            with Container(classes="config-section"):
                yield Label("LLM Provider", classes="config-section-title")
                yield Static("Checking available providers...", id="provider-status")
                with RadioSet(id="provider-select"):
                    yield RadioButton(
                        "Local MLX (checking...)",
                        id="provider-local",
                        disabled=True,
                    )
                    yield RadioButton(
                        "OpenAI (checking...)",
                        id="provider-openai",
                        disabled=True,
                    )
                    yield RadioButton(
                        "Anthropic (checking...)",
                        id="provider-anthropic",
                        disabled=True,
                    )

        yield NavigationBar(show_back=True, show_next=True, next_disabled=True)

    def on_mount(self) -> None:
        self._check_providers()

    @work(exclusive=True)
    async def _check_providers(self) -> None:
        manager = ProviderManager()
        available = await manager.list_available_providers()
        self._available_providers = available

        status = self.query_one("#provider-status", Static)

        if not available:
            status.update("[red]No providers available. Check API keys or install mlx-lm.[/red]")
            return

        count = len(available)
        provider_word = "provider" if count == 1 else "providers"
        status.update(f"[green]{count} {provider_word} available[/green]")

        provider_map = dict(available)

        local_btn = self.query_one("#provider-local", RadioButton)
        if ProviderType.LOCAL in provider_map:
            local_btn.label = f"Local MLX ({provider_map[ProviderType.LOCAL]})"
            local_btn.disabled = False
            local_btn.value = True
            self.state.provider_type = ProviderType.LOCAL
        else:
            local_btn.label = "Local MLX (not available)"

        openai_btn = self.query_one("#provider-openai", RadioButton)
        if ProviderType.OPENAI in provider_map:
            openai_btn.label = f"OpenAI ({provider_map[ProviderType.OPENAI]})"
            openai_btn.disabled = False
            if self.state.provider_type is None:
                openai_btn.value = True
                self.state.provider_type = ProviderType.OPENAI
        else:
            openai_btn.label = "OpenAI (set OPENAI_API_KEY)"

        anthropic_btn = self.query_one("#provider-anthropic", RadioButton)
        if ProviderType.ANTHROPIC in provider_map:
            anthropic_btn.label = f"Anthropic ({provider_map[ProviderType.ANTHROPIC]})"
            anthropic_btn.disabled = False
            if self.state.provider_type is None:
                anthropic_btn.value = True
                self.state.provider_type = ProviderType.ANTHROPIC
        else:
            anthropic_btn.label = "Anthropic (set ANTHROPIC_API_KEY)"

        next_btn = self.query_one("#nav-next", Button)
        next_btn.disabled = len(available) == 0

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "version-select":
            selected_id = event.pressed.id
            if selected_id == "version-sequoia":
                self.state.macos_version = SchemaVersion.SEQUOIA
            elif selected_id == "version-sonoma":
                self.state.macos_version = SchemaVersion.SONOMA
            elif selected_id == "version-tahoe":
                self.state.macos_version = SchemaVersion.TAHOE

        elif event.radio_set.id == "provider-select":
            selected_id = event.pressed.id
            if selected_id == "provider-local":
                self.state.provider_type = ProviderType.LOCAL
            elif selected_id == "provider-openai":
                self.state.provider_type = ProviderType.OPENAI
            elif selected_id == "provider-anthropic":
                self.state.provider_type = ProviderType.ANTHROPIC

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "output-path":
            self.state.output_path = Path(event.value)

    def action_next(self) -> None:
        from imessage_data_foundry.ui.screens.personas import PersonasScreen

        self.app.push_screen(PersonasScreen())
