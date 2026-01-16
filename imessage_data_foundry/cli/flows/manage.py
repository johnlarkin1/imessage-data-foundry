from datetime import UTC, datetime

from rich.console import Console
from rich.panel import Panel

from imessage_data_foundry.cli.components.prompts import (
    confirm_prompt,
    manage_action_prompt,
    persona_input_prompts,
    select_single_persona_prompt,
)
from imessage_data_foundry.cli.components.tables import persona_detail_table, persona_table
from imessage_data_foundry.personas.models import Persona
from imessage_data_foundry.personas.storage import PersonaStorage


def run_manage(console: Console) -> None:
    console.print()
    console.print(Panel("[bold yellow]Manage Personas[/bold yellow]", border_style="yellow"))
    console.print()

    with PersonaStorage() as storage:
        while True:
            personas = storage.list_all()

            if not personas:
                console.print("[yellow]No personas found.[/yellow]")
                console.print("[dim]Use Quick Start or Guided mode to create personas.[/dim]")
                return

            console.print(persona_table(personas))
            console.print()

            action = manage_action_prompt()

            if action == "back":
                return

            if action == "edit":
                _handle_edit(console, storage, personas)
            elif action == "delete":
                _handle_delete(console, storage, personas)


def _handle_edit(console: Console, storage: PersonaStorage, personas: list[Persona]) -> None:
    console.print()
    persona = select_single_persona_prompt(personas, "Select persona to edit")

    if persona is None:
        return

    console.print()
    console.print(persona_detail_table(persona))
    console.print()

    console.print("[dim]Enter new values (press Enter to keep current):[/dim]")
    console.print()

    inputs = persona_input_prompts(is_self=persona.is_self, existing=persona)

    updated = Persona(
        id=persona.id,
        name=inputs["name"],
        identifier=persona.identifier,
        identifier_type=persona.identifier_type,
        country_code=persona.country_code,
        personality=inputs["personality"],
        writing_style=inputs["writing_style"],
        relationship=inputs["relationship"],
        communication_frequency=inputs["communication_frequency"],
        typical_response_time=inputs["typical_response_time"],
        emoji_usage=inputs["emoji_usage"],
        vocabulary_level=inputs["vocabulary_level"],
        topics_of_interest=inputs["topics_of_interest"],
        is_self=persona.is_self,
        created_at=persona.created_at,
        updated_at=datetime.now(UTC),
    )

    storage.update(updated)
    console.print(f"[green]Updated {updated.name}.[/green]")
    console.print()


def _handle_delete(console: Console, storage: PersonaStorage, personas: list[Persona]) -> None:
    console.print()
    persona = select_single_persona_prompt(personas, "Select persona to delete")

    if persona is None:
        return

    console.print()
    console.print(persona_detail_table(persona))
    console.print()

    if persona.is_self:
        console.print("[yellow]Warning: This is your 'self' persona.[/yellow]")
        console.print("[dim]Deleting it will require creating a new one for conversations.[/dim]")
        console.print()

    if confirm_prompt(f"Delete {persona.name}?", default=False):
        storage.delete(persona.id)
        console.print(f"[green]Deleted {persona.name}.[/green]")
    else:
        console.print("[dim]Cancelled.[/dim]")

    console.print()
