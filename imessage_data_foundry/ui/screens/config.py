"""Configuration screen - macOS version, output path, LLM provider."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import Center, VerticalScroll
from textual.widgets import Button, Input, Label, Static

from imessage_data_foundry.db.schema.base import SchemaVersion
from imessage_data_foundry.db.version_detect import detect_schema_version
from imessage_data_foundry.llm.config import ProviderType
from imessage_data_foundry.llm.manager import ProviderManager
from imessage_data_foundry.ui.screens.base import NavigationBar, WizardScreen
from imessage_data_foundry.ui.state import Screen
from imessage_data_foundry.ui.widgets import SectionCard, SelectionCard


class ConfigScreen(WizardScreen):
    """Configuration screen for setting up generation parameters."""

    SCREEN_ID = Screen.CONFIG

    def __init__(self) -> None:
        super().__init__()
        self._available_providers: list[tuple[ProviderType, str]] = []
        self._detected_version = detect_schema_version()

    def body(self) -> ComposeResult:
        with VerticalScroll(id="config-scroll"):
            with Center(), SectionCard("macOS Version", id="section-version"):
                yield SelectionCard(
                    label="Sequoia (macOS 15)",
                    description="Latest schema with full feature support",
                    value="sequoia",
                    selected=self._detected_version == SchemaVersion.SEQUOIA,
                    id="version-sequoia",
                )
                yield SelectionCard(
                    label="Sonoma (macOS 14)",
                    description="Previous major version schema",
                    value="sonoma",
                    selected=self._detected_version == SchemaVersion.SONOMA,
                    id="version-sonoma",
                )
                yield SelectionCard(
                    label="Tahoe (macOS 26)",
                    description="Future version schema (beta)",
                    value="tahoe",
                    selected=self._detected_version == SchemaVersion.TAHOE,
                    id="version-tahoe",
                )

            with Center(), SectionCard("Output Path", id="section-output"):
                yield Input(
                    str(self.state.output_path),
                    id="output-path",
                    placeholder="./output/chat.db",
                )
                yield Label("Database will be created at this location", classes="hint")

            with Center(), SectionCard("LLM Provider", id="section-provider"):
                yield Static("Checking available providers...", id="provider-status")
                yield SelectionCard(
                    label="Local MLX",
                    description="Fast local inference on Apple Silicon",
                    value="local",
                    disabled=True,
                    id="provider-local",
                )
                yield SelectionCard(
                    label="OpenAI",
                    description="GPT-4 via API (requires OPENAI_API_KEY)",
                    value="openai",
                    disabled=True,
                    id="provider-openai",
                )
                yield SelectionCard(
                    label="Anthropic",
                    description="Claude via API (requires ANTHROPIC_API_KEY)",
                    value="anthropic",
                    disabled=True,
                    id="provider-anthropic",
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
            status.update("[#FF3B30]No providers available. Check API keys or install mlx-lm.[/]")
            return

        count = len(available)
        provider_word = "provider" if count == 1 else "providers"
        status.update(f"[#34C759]{count} {provider_word} available[/]")

        provider_map = dict(available)

        local_card = self.query_one("#provider-local", SelectionCard)
        if ProviderType.LOCAL in provider_map:
            local_card._disabled = False
            local_card.remove_class("disabled")
            local_card.can_focus = True
            local_card.description = f"Using {provider_map[ProviderType.LOCAL]}"
            local_card.selected = True
            self.state.provider_type = ProviderType.LOCAL

        openai_card = self.query_one("#provider-openai", SelectionCard)
        if ProviderType.OPENAI in provider_map:
            openai_card._disabled = False
            openai_card.remove_class("disabled")
            openai_card.can_focus = True
            openai_card.description = f"Using {provider_map[ProviderType.OPENAI]}"
            if self.state.provider_type is None:
                openai_card.selected = True
                self.state.provider_type = ProviderType.OPENAI

        anthropic_card = self.query_one("#provider-anthropic", SelectionCard)
        if ProviderType.ANTHROPIC in provider_map:
            anthropic_card._disabled = False
            anthropic_card.remove_class("disabled")
            anthropic_card.can_focus = True
            anthropic_card.description = f"Using {provider_map[ProviderType.ANTHROPIC]}"
            if self.state.provider_type is None:
                anthropic_card.selected = True
                self.state.provider_type = ProviderType.ANTHROPIC

        next_btn = self.query_one("#nav-next", Button)
        next_btn.disabled = len(available) == 0

    def on_selection_card_selected(self, event: SelectionCard.Selected) -> None:
        card_id = event.card.id or ""

        if card_id.startswith("version-"):
            for card in self.query(SelectionCard):
                if card.id and card.id.startswith("version-"):
                    card.selected = card.id == card_id

            if card_id == "version-sequoia":
                self.state.macos_version = SchemaVersion.SEQUOIA
            elif card_id == "version-sonoma":
                self.state.macos_version = SchemaVersion.SONOMA
            elif card_id == "version-tahoe":
                self.state.macos_version = SchemaVersion.TAHOE

        elif card_id.startswith("provider-"):
            for card in self.query(SelectionCard):
                if card.id and card.id.startswith("provider-") and not card._disabled:
                    card.selected = card.id == card_id

            if card_id == "provider-local":
                self.state.provider_type = ProviderType.LOCAL
            elif card_id == "provider-openai":
                self.state.provider_type = ProviderType.OPENAI
            elif card_id == "provider-anthropic":
                self.state.provider_type = ProviderType.ANTHROPIC

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "output-path":
            self.state.output_path = Path(event.value)

    def action_next(self) -> None:
        from imessage_data_foundry.ui.screens.personas import PersonasScreen

        self.app.push_screen(PersonasScreen())
