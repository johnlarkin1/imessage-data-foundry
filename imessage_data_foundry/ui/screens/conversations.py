"""Conversations screen - configure conversation parameters."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, Select, Static, TextArea

from imessage_data_foundry.personas.models import ChatType, ServiceType
from imessage_data_foundry.personas.storage import PersonaStorage
from imessage_data_foundry.ui.screens.base import NavigationBar, WizardScreen
from imessage_data_foundry.ui.state import Screen


class ConversationsScreen(WizardScreen):
    """Configure conversation parameters before generation."""

    SCREEN_ID = Screen.CONVERSATIONS

    def body(self) -> ComposeResult:
        with Vertical(id="conversation-config"):
            yield Label("Selected Personas", classes="section-label")
            yield Static("Loading...", id="selected-personas-display")

            yield Label("Message Count", classes="section-label")
            yield Input(
                str(self.state.message_count),
                id="message-count",
                placeholder="100",
                type="integer",
            )
            yield Label("(1 - 10,000 messages)", classes="hint")

            yield Label("Time Range", classes="section-label")
            with Horizontal(id="time-range"):
                yield Label("Days ago: ")
                yield Input(
                    "30",
                    id="days-ago",
                    type="integer",
                )
            yield Label(
                "Messages will be distributed across this time range",
                classes="hint",
            )

            yield Label("Chat Type", classes="section-label")
            yield Select(
                [
                    ("Direct (2 people)", ChatType.DIRECT.value),
                    ("Group chat", ChatType.GROUP.value),
                ],
                value=ChatType.DIRECT.value,
                id="chat-type",
            )

            yield Label("Service", classes="section-label")
            yield Select(
                [
                    ("iMessage", ServiceType.IMESSAGE.value),
                    ("SMS", ServiceType.SMS.value),
                ],
                value=ServiceType.IMESSAGE.value,
                id="service-type",
            )

            yield Label("Conversation Seed (optional)", classes="section-label")
            yield TextArea(
                id="conversation-seed",
                classes="seed-input",
            )
            yield Label(
                "Provide a theme or topic to guide the conversation",
                classes="hint",
            )

            yield Static("", id="validation-message")

        yield NavigationBar(show_back=True, show_next=True, next_label="Generate")

    def on_mount(self) -> None:
        self._display_selected_personas()
        self._validate_config()

    def _display_selected_personas(self) -> None:
        with PersonaStorage() as storage:
            all_personas = storage.list_all()

        selected = [p for p in all_personas if p.id in self.state.selected_persona_ids]
        display = self.query_one("#selected-personas-display", Static)

        if not selected:
            display.update("[red]No personas selected[/red]")
            return

        names = []
        for p in selected:
            if p.is_self:
                names.append(f"[bold]{p.name}[/bold] (you)")
            else:
                names.append(p.name)

        display.update(" | ".join(names))

        chat_type_select = self.query_one("#chat-type", Select)
        if len(selected) > 2:
            chat_type_select.value = ChatType.GROUP.value

    def _validate_config(self) -> bool:
        validation_msg = self.query_one("#validation-message", Static)
        errors = []

        try:
            count_input = self.query_one("#message-count", Input)
            count = int(count_input.value) if count_input.value else 0
            if count < 1 or count > 10000:
                errors.append("Message count must be between 1 and 10,000")
        except ValueError:
            errors.append("Invalid message count")

        try:
            days_input = self.query_one("#days-ago", Input)
            days = int(days_input.value) if days_input.value else 0
            if days < 1:
                errors.append("Days must be at least 1")
        except ValueError:
            errors.append("Invalid days value")

        selected_count = len(self.state.selected_persona_ids)
        if selected_count < 2:
            errors.append("Need at least 2 personas selected")

        try:
            chat_type_select = self.query_one("#chat-type", Select)
            if chat_type_select.value == ChatType.DIRECT.value and selected_count > 2:
                errors.append("Direct chat can only have 2 participants")
        except Exception:
            pass

        if errors:
            validation_msg.update("[red]" + " | ".join(errors) + "[/red]")
            return False
        else:
            validation_msg.update("[green]Ready to generate[/green]")
            return True

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "message-count":
            with contextlib.suppress(ValueError):
                self.state.message_count = int(event.value) if event.value else 100
        elif event.input.id == "days-ago":
            with contextlib.suppress(ValueError):
                days = int(event.value) if event.value else 30
                now = datetime.now(UTC)
                self.state.time_range_start = now - timedelta(days=days)
                self.state.time_range_end = now

        self._validate_config()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "service-type":
            self.state.service = ServiceType(event.value)
        self._validate_config()

    def _save_config(self) -> None:
        try:
            count_input = self.query_one("#message-count", Input)
            self.state.message_count = int(count_input.value) if count_input.value else 100
        except ValueError:
            self.state.message_count = 100

        try:
            days_input = self.query_one("#days-ago", Input)
            days = int(days_input.value) if days_input.value else 30
            now = datetime.now(UTC)
            self.state.time_range_start = now - timedelta(days=days)
            self.state.time_range_end = now
        except ValueError:
            pass

        seed_area = self.query_one("#conversation-seed", TextArea)
        seed_text = seed_area.text.strip()
        self.state.seed = seed_text if seed_text else None

        service_select = self.query_one("#service-type", Select)
        self.state.service = ServiceType(service_select.value)

    def action_next(self) -> None:
        if not self._validate_config():
            self.notify("Please fix validation errors", severity="error")
            return

        self._save_config()

        from imessage_data_foundry.ui.screens.generation import GenerationScreen

        self.app.push_screen(GenerationScreen())
