"""Conversations screen - configure conversation parameters."""

from __future__ import annotations

import contextlib
import random
from datetime import UTC, datetime, timedelta

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Button, Input, Label, Select, Static, TextArea

from imessage_data_foundry.personas.models import ChatType, ServiceType
from imessage_data_foundry.personas.storage import PersonaStorage
from imessage_data_foundry.ui.screens.base import NavigationBar, WizardScreen
from imessage_data_foundry.ui.state import Screen
from imessage_data_foundry.ui.widgets import AvatarCircle, SectionCard


class ConversationsScreen(WizardScreen):
    """Configure conversation parameters before generation."""

    SCREEN_ID = Screen.CONVERSATIONS

    def body(self) -> ComposeResult:
        with VerticalScroll(id="conversation-config"):
            with (
                SectionCard("Participants"),
                Horizontal(id="selected-personas-display", classes="personas-row"),
            ):
                yield Static("Loading...", id="personas-placeholder")

            with SectionCard("Message Settings"):
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

            with SectionCard("Chat Options"):
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

            with SectionCard("Conversation Seed (optional)"):
                yield Label("[dim]Give the AI a topic to discuss[/]", classes="hint")
                yield TextArea(id="conversation-seed", classes="seed-input")
                with Horizontal(classes="field-with-action"):
                    yield Button(
                        "Suggest Topic",
                        id="suggest-seed-btn",
                        variant="default",
                        classes="small-btn",
                    )
                    yield Static("", id="seed-status", classes="loading-status")

            yield Static("", id="validation-message")

        yield NavigationBar(show_back=True, show_next=True, next_label="Generate")

    def on_mount(self) -> None:
        self._display_selected_personas()
        self._validate_config()

    def _display_selected_personas(self) -> None:
        with PersonaStorage() as storage:
            all_personas = storage.list_all()

        selected = [p for p in all_personas if p.id in self.state.selected_persona_ids]

        try:
            display = self.query_one("#selected-personas-display", Horizontal)
            display.remove_children()

            if not selected:
                display.mount(Static("[#FF3B30]No personas selected[/]"))
                return

            for p in selected:
                with Container(classes="avatar-badge"):
                    display.mount(AvatarCircle(p.name, p.is_self, small=False))

            chat_type_select = self.query_one("#chat-type", Select)
            if len(selected) > 2:
                chat_type_select.value = ChatType.GROUP.value
        except Exception:
            pass

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
            validation_msg.update("[#FF3B30]" + " | ".join(errors) + "[/]")
            return False
        else:
            validation_msg.update("[#34C759]Ready to generate[/]")
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "suggest-seed-btn":
            self._suggest_seed()

    @work(exclusive=True, group="seed-suggest")
    async def _suggest_seed(self) -> None:
        """Suggest a conversation seed based on selected personas."""
        try:
            status = self.query_one("#seed-status", Static)
            status.update("[#007AFF]Thinking...[/]")
        except Exception:
            return

        try:
            with PersonaStorage() as storage:
                all_personas = storage.list_all()
            selected = [p for p in all_personas if p.id in self.state.selected_persona_ids]

            seed_templates = [
                "Catching up after not talking for a while",
                "Making plans for the weekend",
                "Sharing something funny that happened today",
                "Asking for advice about a decision",
                "Discussing a new restaurant to try",
                "Planning a birthday surprise",
                "Talking about a movie or TV show",
                "Reminiscing about old memories",
                "Venting about a frustrating day at work",
                "Coordinating logistics for an event",
            ]

            relationships = [p.relationship for p in selected if p.relationship and not p.is_self]
            if relationships:
                rel = relationships[0].lower()
                if "family" in rel or "parent" in rel or "sibling" in rel:
                    seed_templates.extend(
                        [
                            "Planning a family dinner",
                            "Discussing upcoming holidays",
                            "Checking in on how everyone is doing",
                        ]
                    )
                elif "coworker" in rel or "colleague" in rel or "work" in rel:
                    seed_templates.extend(
                        [
                            "Discussing a project deadline",
                            "Planning after-work drinks",
                            "Venting about a difficult meeting",
                        ]
                    )
                elif "friend" in rel:
                    seed_templates.extend(
                        [
                            "Planning a game night",
                            "Discussing weekend plans",
                            "Sharing exciting news",
                        ]
                    )

            seed = random.choice(seed_templates)

            seed_area = self.query_one("#conversation-seed", TextArea)
            seed_area.load_text(seed)
            status.update("")

        except Exception as e:
            try:
                status = self.query_one("#seed-status", Static)
                status.update(f"[#FF3B30]Error: {e!s}[/]")
            except Exception:
                pass

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
