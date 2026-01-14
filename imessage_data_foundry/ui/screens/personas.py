"""Personas screen - manage and select personas for conversation."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Checkbox, Input, Label, Select, Static, TextArea

from imessage_data_foundry.personas.models import (
    CommunicationFrequency,
    EmojiUsage,
    IdentifierType,
    Persona,
    ResponseTime,
    VocabularyLevel,
)
from imessage_data_foundry.personas.storage import PersonaStorage
from imessage_data_foundry.ui.screens.base import NavigationBar, WizardScreen
from imessage_data_foundry.ui.state import Screen


class PersonaCard(Static):
    """Widget displaying a persona with selection checkbox."""

    DEFAULT_CSS = """
    PersonaCard {
        height: auto;
        padding: 1;
        margin: 0 0 1 0;
        border: solid $primary;
    }
    PersonaCard.selected {
        border: double $success;
        background: $success-darken-3;
    }
    PersonaCard .persona-header {
        height: 1;
    }
    PersonaCard .persona-name {
        text-style: bold;
    }
    PersonaCard .persona-details {
        color: $text-muted;
    }
    PersonaCard .self-badge {
        color: $warning;
        text-style: bold;
    }
    """

    def __init__(self, persona: Persona, is_selected: bool = False) -> None:
        super().__init__()
        self.persona = persona
        self._is_selected = is_selected
        if is_selected:
            self.add_class("selected")

    def compose(self) -> ComposeResult:
        p = self.persona
        with Horizontal(classes="persona-header"):
            yield Checkbox(
                p.name,
                value=self._is_selected,
                id=f"select-{p.id}",
            )
            if p.is_self:
                yield Label(" [SELF]", classes="self-badge")
        yield Label(f"  {p.display_identifier} | {p.relationship}", classes="persona-details")
        if p.personality:
            preview = p.personality[:60] + "..." if len(p.personality) > 60 else p.personality
            yield Label(f"  {preview}", classes="persona-details")


class CreatePersonaForm(Container):
    """Form for creating a new persona."""

    DEFAULT_CSS = """
    CreatePersonaForm {
        height: auto;
        padding: 1;
        border: solid $primary;
        margin: 1;
    }
    CreatePersonaForm Label {
        margin-top: 1;
    }
    CreatePersonaForm Input, CreatePersonaForm Select, CreatePersonaForm TextArea {
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Create New Persona", classes="section-label")

        yield Label("Name *")
        yield Input(placeholder="Alice", id="persona-name")

        yield Label("Identifier * (phone or email)")
        yield Input(placeholder="+15551234567", id="persona-identifier")

        yield Label("Identifier Type")
        yield Select(
            [(t.value, t.value) for t in IdentifierType],
            value=IdentifierType.PHONE.value,
            id="persona-id-type",
        )

        yield Label("Relationship")
        yield Input(value="friend", id="persona-relationship")

        yield Label("Personality")
        yield TextArea(id="persona-personality")

        yield Label("Writing Style")
        yield Input(value="casual", id="persona-style")

        yield Label("Communication Frequency")
        yield Select(
            [(f.value, f.value) for f in CommunicationFrequency],
            value=CommunicationFrequency.MEDIUM.value,
            id="persona-frequency",
        )

        yield Label("Response Time")
        yield Select(
            [(r.value, r.value) for r in ResponseTime],
            value=ResponseTime.MINUTES.value,
            id="persona-response-time",
        )

        yield Label("Emoji Usage")
        yield Select(
            [(e.value, e.value) for e in EmojiUsage],
            value=EmojiUsage.LIGHT.value,
            id="persona-emoji",
        )

        yield Label("Vocabulary Level")
        yield Select(
            [(v.value, v.value) for v in VocabularyLevel],
            value=VocabularyLevel.MODERATE.value,
            id="persona-vocabulary",
        )

        yield Checkbox("This is me (self)", id="persona-is-self")

        with Horizontal():
            yield Button("Create", id="create-persona-btn", variant="primary")
            yield Button("Cancel", id="cancel-create-btn", variant="default")


class PersonasScreen(WizardScreen):
    """Persona management and selection screen."""

    SCREEN_ID = Screen.PERSONAS

    def __init__(self) -> None:
        super().__init__()
        self._personas: list[Persona] = []
        self._show_create_form = False

    def body(self) -> ComposeResult:
        with Horizontal(id="personas-layout"):
            with Vertical(id="personas-list-panel"):
                yield Label("Select Personas", classes="section-label")
                yield Label(
                    "Select at least 2 personas (one must be marked as 'self')",
                    id="selection-hint",
                )
                with VerticalScroll(id="personas-list"):
                    yield Static("Loading personas...", id="personas-loading")

                with Horizontal(id="personas-actions"):
                    yield Button("Create New", id="show-create-btn", variant="primary")
                    yield Button("Refresh", id="refresh-btn", variant="default")

            with Container(id="create-form-panel"):
                if self._show_create_form:
                    yield CreatePersonaForm()
                else:
                    yield Static("", id="form-placeholder")

        yield NavigationBar(show_back=True, show_next=True, next_disabled=True)

    def on_mount(self) -> None:
        self._load_personas()

    def _load_personas(self) -> None:
        with PersonaStorage() as storage:
            self._personas = storage.list_all()

        personas_list = self.query_one("#personas-list", VerticalScroll)
        personas_list.remove_children()

        if not self._personas:
            personas_list.mount(
                Static(
                    "No personas found. Create one to get started.",
                    id="no-personas",
                )
            )
        else:
            for persona in self._personas:
                is_selected = persona.id in self.state.selected_persona_ids
                personas_list.mount(PersonaCard(persona, is_selected))

        self._update_next_button()

    def _update_next_button(self) -> None:
        try:
            next_btn = self.query_one("#nav-next", Button)
        except Exception:
            return

        selected_ids = self.state.selected_persona_ids
        selected_personas = [p for p in self._personas if p.id in selected_ids]

        has_self = any(p.is_self for p in selected_personas)
        has_enough = len(selected_personas) >= 2

        next_btn.disabled = not (has_self and has_enough)

        try:
            hint = self.query_one("#selection-hint", Label)
            if not selected_ids:
                hint.update("Select at least 2 personas (one must be marked as 'self')")
            elif not has_self:
                hint.update(
                    f"[yellow]{len(selected_ids)} selected - need one marked as 'self'[/yellow]"
                )
            elif not has_enough:
                hint.update(f"[yellow]{len(selected_ids)} selected - need at least 2[/yellow]")
            else:
                hint.update(f"[green]{len(selected_ids)} personas selected[/green]")
        except Exception:
            pass

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        checkbox_id = event.checkbox.id or ""
        if checkbox_id.startswith("select-"):
            persona_id = checkbox_id[7:]
            if event.value:
                if persona_id not in self.state.selected_persona_ids:
                    self.state.selected_persona_ids.append(persona_id)
            else:
                if persona_id in self.state.selected_persona_ids:
                    self.state.selected_persona_ids.remove(persona_id)

            self._update_card_styling(persona_id, event.value)
            self._update_next_button()

    def _update_card_styling(self, persona_id: str, is_selected: bool) -> None:
        for card in self.query(PersonaCard):
            if card.persona.id == persona_id:
                if is_selected:
                    card.add_class("selected")
                else:
                    card.remove_class("selected")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "show-create-btn":
            self._toggle_create_form(True)
        elif event.button.id == "cancel-create-btn":
            self._toggle_create_form(False)
        elif event.button.id == "refresh-btn":
            self._load_personas()
        elif event.button.id == "create-persona-btn":
            self._create_persona()

    def _toggle_create_form(self, show: bool) -> None:
        form_panel = self.query_one("#create-form-panel", Container)
        form_panel.remove_children()
        if show:
            form_panel.mount(CreatePersonaForm())
        else:
            form_panel.mount(Static("", id="form-placeholder"))
        self._show_create_form = show

    def _create_persona(self) -> None:
        try:
            name = self.query_one("#persona-name", Input).value.strip()
            identifier = self.query_one("#persona-identifier", Input).value.strip()

            if not name or not identifier:
                self.notify("Name and identifier are required", severity="error")
                return

            id_type_select = self.query_one("#persona-id-type", Select)
            id_type = IdentifierType(id_type_select.value)

            relationship = self.query_one("#persona-relationship", Input).value.strip() or "friend"

            personality_area = self.query_one("#persona-personality", TextArea)
            personality = personality_area.text.strip()

            style = self.query_one("#persona-style", Input).value.strip() or "casual"

            freq_select = self.query_one("#persona-frequency", Select)
            frequency = CommunicationFrequency(freq_select.value)

            resp_select = self.query_one("#persona-response-time", Select)
            response_time = ResponseTime(resp_select.value)

            emoji_select = self.query_one("#persona-emoji", Select)
            emoji = EmojiUsage(emoji_select.value)

            vocab_select = self.query_one("#persona-vocabulary", Select)
            vocabulary = VocabularyLevel(vocab_select.value)

            is_self = self.query_one("#persona-is-self", Checkbox).value

            persona = Persona(
                name=name,
                identifier=identifier,
                identifier_type=id_type,
                relationship=relationship,
                personality=personality,
                writing_style=style,
                communication_frequency=frequency,
                typical_response_time=response_time,
                emoji_usage=emoji,
                vocabulary_level=vocabulary,
                is_self=is_self,
            )

            with PersonaStorage() as storage:
                storage.create(persona)

            self.notify(f"Created persona: {name}", severity="information")
            self._toggle_create_form(False)
            self._load_personas()

        except Exception as e:
            self.notify(f"Error creating persona: {e}", severity="error")

    def action_next(self) -> None:
        from imessage_data_foundry.ui.screens.conversations import ConversationsScreen

        self.app.push_screen(ConversationsScreen())
