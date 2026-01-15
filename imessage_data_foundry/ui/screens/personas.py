"""Personas screen - manage and select personas for conversation."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Checkbox, Input, Label, Select, Static, TextArea

from imessage_data_foundry.llm.manager import ProviderManager
from imessage_data_foundry.llm.models import PersonaConstraints
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
from imessage_data_foundry.ui.widgets import AvatarCircle


class PersonaCard(Static):
    """Widget displaying a persona with selection checkbox and avatar."""

    def __init__(self, persona: Persona, is_selected: bool = False) -> None:
        super().__init__()
        self.persona = persona
        self._is_selected = is_selected
        if is_selected:
            self.add_class("selected")

    def compose(self) -> ComposeResult:
        p = self.persona
        with Horizontal(classes="persona-row"):
            with Container(classes="avatar-section"):
                yield AvatarCircle(p.name, p.is_self)
            with Vertical(classes="info-section"):
                with Horizontal(classes="persona-header"):
                    yield Checkbox(
                        p.name,
                        value=self._is_selected,
                        id=f"select-{p.id}",
                        classes="persona-name",
                    )
                    if p.is_self:
                        yield Label("YOU", classes="self-badge")
                yield Label(
                    f"{p.display_identifier}  |  {p.relationship}",
                    classes="persona-identifier",
                )
                if p.personality:
                    preview = (
                        p.personality[:50] + "..." if len(p.personality) > 50 else p.personality
                    )
                    yield Label(preview, classes="persona-details")


class CreatePersonaForm(VerticalScroll):
    """Form for creating a new persona."""

    def compose(self) -> ComposeResult:
        yield Label("Create New Persona", classes="form-title")
        yield Label(
            "[dim]Fill in details manually or use AI to generate[/]",
            classes="form-subtitle",
        )

        yield Label("Name *")
        yield Input(placeholder="e.g. Alice Smith", id="persona-name")

        yield Label("Phone/Email *")
        yield Input(placeholder="e.g. +15551234567", id="persona-identifier")

        yield Label("Identifier Type")
        yield Select(
            [(t.value, t.value) for t in IdentifierType],
            value=IdentifierType.PHONE.value,
            id="persona-id-type",
        )

        yield Label("Relationship to you")
        yield Input(
            placeholder="e.g. friend, coworker, family", value="friend", id="persona-relationship"
        )

        yield Label("Personality [dim](optional - describe their traits)[/]")
        yield TextArea(id="persona-personality")

        with Horizontal(classes="field-with-action"):
            yield Button(
                "AI Generate", id="generate-fields-btn", variant="primary", classes="small-btn"
            )
            yield Label("[dim]Fill personality & style using AI[/]", classes="btn-hint")
        yield Static("", id="generate-status", classes="loading-status")

        yield Label("Writing Style")
        yield Input(
            placeholder="e.g. casual, formal, uses slang", value="casual", id="persona-style"
        )

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

        yield Checkbox("This is me (the 'self' in conversations)", id="persona-is-self")

        yield Static("")  # Spacer

        with Horizontal(classes="form-actions"):
            yield Button("Create", id="create-persona-btn", variant="primary")
            yield Button("AI Create All", id="auto-generate-btn", variant="success")
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
                    "No personas found.\nCreate one to get started.",
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
                hint.update(f"[#FF9500]{len(selected_ids)} selected - need one marked as 'self'[/]")
            elif not has_enough:
                hint.update(f"[#FF9500]{len(selected_ids)} selected - need at least 2[/]")
            else:
                hint.update(f"[#34C759]{len(selected_ids)} personas selected[/]")
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
        elif event.button.id == "generate-fields-btn":
            self._generate_persona_fields()
        elif event.button.id == "auto-generate-btn":
            self._auto_generate_persona()

    def _toggle_create_form(self, show: bool) -> None:
        form_panel = self.query_one("#create-form-panel", Container)
        form_panel.remove_children()
        if show:
            form_panel.mount(CreatePersonaForm())
            self.call_after_refresh(self._focus_form_name)
        else:
            form_panel.mount(Static("", id="form-placeholder"))
        self._show_create_form = show

    def _focus_form_name(self) -> None:
        try:
            name_input = self.query_one("#persona-name", Input)
            name_input.focus()
        except Exception:
            pass

    @work(exclusive=True, group="llm-generate")
    async def _generate_persona_fields(self) -> None:
        """Generate personality and style fields using LLM."""
        import random

        try:
            status = self.query_one("#generate-status", Static)
            status.update("[#007AFF]Generating with AI...[/]")
        except Exception:
            return

        try:
            name_input = self.query_one("#persona-name", Input)
            relationship = self.query_one("#persona-relationship", Input).value.strip()

            constraints = PersonaConstraints(
                relationship=relationship if relationship else "friend",
            )

            provider_type = getattr(self.state, "provider_type", None)
            manager = ProviderManager()
            provider = await manager.get_provider(provider_type)

            personas = await provider.generate_personas(constraints=constraints, count=1)

            if personas:
                generated = personas[0]

                # Fill name if empty
                if not name_input.value.strip():
                    name_input.value = generated.name

                # Fill identifier if empty
                identifier_input = self.query_one("#persona-identifier", Input)
                if not identifier_input.value.strip():
                    identifier_input.value = f"+1555{random.randint(1000000, 9999999)}"

                # Fill relationship if default
                relationship_input = self.query_one("#persona-relationship", Input)
                if (
                    relationship_input.value.strip() == "friend"
                    or not relationship_input.value.strip()
                ):
                    relationship_input.value = generated.relationship

                personality_area = self.query_one("#persona-personality", TextArea)
                personality_area.load_text(generated.personality)

                style_input = self.query_one("#persona-style", Input)
                style_input.value = generated.writing_style

                freq_select = self.query_one("#persona-frequency", Select)
                freq_select.value = generated.communication_frequency

                emoji_select = self.query_one("#persona-emoji", Select)
                emoji_select.value = generated.emoji_usage

                vocab_select = self.query_one("#persona-vocabulary", Select)
                vocab_select.value = generated.vocabulary_level

                resp_select = self.query_one("#persona-response-time", Select)
                resp_select.value = generated.typical_response_time

                status.update("[#34C759]Done! Review and click Create[/]")
            else:
                status.update("[#FF3B30]Generation failed[/]")

        except Exception as e:
            try:
                status = self.query_one("#generate-status", Static)
                status.update(f"[#FF3B30]Error: {e!s}[/]")
            except Exception:
                self.notify(f"Generation error: {e}", severity="error")

    @work(exclusive=True, group="llm-generate")
    async def _auto_generate_persona(self) -> None:
        """Auto-generate a complete persona with LLM."""
        import random

        try:
            status = self.query_one("#generate-status", Static)
            status.update("[#007AFF]Generating complete persona...[/]")
        except Exception:
            return

        try:
            relationship = self.query_one("#persona-relationship", Input).value.strip()
            is_self = self.query_one("#persona-is-self", Checkbox).value

            constraints = PersonaConstraints(
                relationship="self" if is_self else (relationship or "friend"),
            )

            provider_type = getattr(self.state, "provider_type", None)
            manager = ProviderManager()
            provider = await manager.get_provider(provider_type)

            personas = await provider.generate_personas(constraints=constraints, count=1)

            if personas:
                generated = personas[0]

                name_input = self.query_one("#persona-name", Input)
                name_input.value = generated.name

                identifier_input = self.query_one("#persona-identifier", Input)
                identifier_input.value = f"+1555{random.randint(1000000, 9999999)}"

                personality_area = self.query_one("#persona-personality", TextArea)
                personality_area.load_text(generated.personality)

                style_input = self.query_one("#persona-style", Input)
                style_input.value = generated.writing_style

                relationship_input = self.query_one("#persona-relationship", Input)
                relationship_input.value = generated.relationship

                freq_select = self.query_one("#persona-frequency", Select)
                freq_select.value = generated.communication_frequency

                emoji_select = self.query_one("#persona-emoji", Select)
                emoji_select.value = generated.emoji_usage

                vocab_select = self.query_one("#persona-vocabulary", Select)
                vocab_select.value = generated.vocabulary_level

                resp_select = self.query_one("#persona-response-time", Select)
                resp_select.value = generated.typical_response_time

                status.update("[#34C759]Generated! Review and click Create[/]")
            else:
                status.update("[#FF3B30]No persona generated[/]")

        except Exception as e:
            try:
                status = self.query_one("#generate-status", Static)
                status.update(f"[#FF3B30]Error: {e!s}[/]")
            except Exception:
                self.notify(f"Generation error: {e}", severity="error")

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
