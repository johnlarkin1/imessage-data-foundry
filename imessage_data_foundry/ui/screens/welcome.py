"""Welcome screen - entry point for the TUI wizard."""

from __future__ import annotations

import random

from textual import work
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.widgets import Button, Label, Static

from imessage_data_foundry.llm.manager import ProviderManager, ProviderNotAvailableError
from imessage_data_foundry.llm.models import PersonaConstraints
from imessage_data_foundry.personas.models import (
    CommunicationFrequency,
    EmojiUsage,
    Persona,
    ResponseTime,
    VocabularyLevel,
)
from imessage_data_foundry.personas.storage import PersonaStorage
from imessage_data_foundry.ui.screens.base import WizardScreen
from imessage_data_foundry.ui.state import Screen


class WelcomeScreen(WizardScreen):
    """Welcome screen with app overview and quick actions."""

    SCREEN_ID = Screen.WELCOME

    def body(self) -> ComposeResult:
        with Center(id="welcome-center"), Vertical(id="welcome-content"):
            yield Static(
                "[bold]iMessage Data Foundry[/]",
                id="app-header",
            )
            yield Label(
                "Generate realistic iMessage databases\nfor testing and development",
                id="tagline",
            )
            with Horizontal(id="button-row"):
                yield Button(
                    "Start Wizard",
                    id="start-wizard",
                    variant="primary",
                )
                yield Button(
                    "Quick Start",
                    id="quick-start",
                    variant="success",
                )
                yield Button(
                    "Manage Personas",
                    id="manage-personas",
                    variant="default",
                )
            yield Static("", id="quick-start-status")
            yield Label(
                "[dim]Press[/] [bold]q[/bold] [dim]to quit  |  [/][bold]Enter[/bold] [dim]to start[/]",
                id="hint",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-wizard":
            self.action_next()
        elif event.button.id == "quick-start":
            self._quick_start()
        elif event.button.id == "manage-personas":
            from imessage_data_foundry.ui.screens.personas import PersonasScreen

            self.app.push_screen(PersonasScreen())

    @work(exclusive=True)
    async def _quick_start(self) -> None:
        """Generate everything automatically and start generation."""
        try:
            status = self.query_one("#quick-start-status", Static)
            status.update("[#007AFF]Setting up quick start...[/]")
        except Exception:
            return

        try:
            manager = ProviderManager()
            try:
                provider = await manager.get_provider()
            except ProviderNotAvailableError:
                status.update("[#FF3B30]No LLM provider available. Use Start Wizard instead.[/]")
                return

            status.update("[#007AFF]Generating personas...[/]")

            self_constraints = PersonaConstraints(relationship="self")
            self_personas = await provider.generate_personas(self_constraints, count=1)

            contact_constraints = PersonaConstraints(relationship="friend")
            contact_personas = await provider.generate_personas(contact_constraints, count=1)

            if not self_personas or not contact_personas:
                status.update("[#FF3B30]Failed to generate personas[/]")
                return

            with PersonaStorage() as storage:
                self_p = self_personas[0]
                self_persona = Persona(
                    name=self_p.name,
                    identifier=f"+1555{random.randint(1000000, 9999999)}",
                    personality=self_p.personality,
                    writing_style=self_p.writing_style,
                    communication_frequency=CommunicationFrequency(self_p.communication_frequency),
                    typical_response_time=ResponseTime(self_p.typical_response_time),
                    emoji_usage=EmojiUsage(self_p.emoji_usage),
                    vocabulary_level=VocabularyLevel(self_p.vocabulary_level),
                    is_self=True,
                )
                storage.create(self_persona)

                contact_p = contact_personas[0]
                contact_persona = Persona(
                    name=contact_p.name,
                    identifier=f"+1555{random.randint(1000000, 9999999)}",
                    relationship=contact_p.relationship,
                    personality=contact_p.personality,
                    writing_style=contact_p.writing_style,
                    communication_frequency=CommunicationFrequency(
                        contact_p.communication_frequency
                    ),
                    typical_response_time=ResponseTime(contact_p.typical_response_time),
                    emoji_usage=EmojiUsage(contact_p.emoji_usage),
                    vocabulary_level=VocabularyLevel(contact_p.vocabulary_level),
                    is_self=False,
                )
                storage.create(contact_persona)

                self.state.selected_persona_ids = [self_persona.id, contact_persona.id]

            status.update("[#34C759]Ready! Starting generation...[/]")

            from imessage_data_foundry.ui.screens.generation import GenerationScreen

            self.app.push_screen(GenerationScreen())

        except Exception as e:
            try:
                status = self.query_one("#quick-start-status", Static)
                status.update(f"[#FF3B30]Error: {e!s}[/]")
            except Exception:
                self.notify(f"Quick start error: {e}", severity="error")

    def action_next(self) -> None:
        from imessage_data_foundry.ui.screens.config import ConfigScreen

        self.app.push_screen(ConfigScreen())

    def action_back(self) -> None:
        pass
