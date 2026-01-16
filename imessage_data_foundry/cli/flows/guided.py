import asyncio
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

from imessage_data_foundry.cli.components.progress import (
    create_generation_progress,
    create_progress_callback,
)
from imessage_data_foundry.cli.components.prompts import (
    confirm_prompt,
    conversation_seed_prompt,
    int_prompt,
    persona_input_prompts,
    select_personas_prompt,
    simulation_type_prompt,
)
from imessage_data_foundry.cli.components.tables import (
    generation_stats_table,
    message_preview_table,
    persona_table,
)
from imessage_data_foundry.cli.provider_helper import get_provider_with_preference
from imessage_data_foundry.cli.utils import (
    DEFAULT_MESSAGE_COUNT,
    DatabaseExistsAction,
    ensure_output_dir,
    get_addressbook_path,
    get_default_time_range,
    handle_existing_database,
    prompt_use_existing_self,
)
from imessage_data_foundry.conversations.generator import (
    ConversationGenerator,
    GenerationResult,
    TimestampedMessage,
)
from imessage_data_foundry.db.addressbook import AddressBookBuilder
from imessage_data_foundry.db.builder import DatabaseBuilder
from imessage_data_foundry.llm.manager import ProviderManager
from imessage_data_foundry.personas.models import (
    ChatType,
    ConversationConfig,
    IdentifierType,
    Persona,
    ServiceType,
)
from imessage_data_foundry.personas.storage import PersonaStorage
from imessage_data_foundry.utils.phone_numbers import generate_fake_phone


def create_persona_from_input(inputs: dict[str, Any], is_self: bool = False) -> Persona:
    return Persona(
        name=inputs["name"],
        identifier=generate_fake_phone("US"),
        identifier_type=IdentifierType.PHONE,
        country_code="US",
        personality=inputs["personality"],
        writing_style=inputs["writing_style"],
        relationship=inputs["relationship"],
        communication_frequency=inputs["communication_frequency"],
        typical_response_time=inputs["typical_response_time"],
        emoji_usage=inputs["emoji_usage"],
        vocabulary_level=inputs["vocabulary_level"],
        topics_of_interest=inputs["topics_of_interest"],
        is_self=is_self,
    )


def run_guided(console: Console) -> Path | None:
    console.print()
    console.print(Panel("[bold blue]Guided Mode[/bold blue]", border_style="blue"))
    console.print()

    action, output_path = handle_existing_database(ensure_output_dir())

    if action == DatabaseExistsAction.CANCEL:
        console.print("[yellow]Cancelled.[/yellow]")
        return None

    append_mode = action == DatabaseExistsAction.APPEND

    self_persona = None
    with PersonaStorage() as storage:
        if append_mode:
            existing_self = storage.get_self()
            if existing_self:
                use_existing = prompt_use_existing_self(existing_self)
                if use_existing:
                    self_persona = existing_self
                    console.print(f"[dim]Using existing self: {existing_self.name}[/dim]")
                else:
                    storage.delete(existing_self.id)
        else:
            for existing in storage.list_all():
                storage.delete(existing.id)

    if self_persona is None:
        console.print("[bold]Step 1: Create Your Persona[/bold]")
        console.print("[dim]First, let's create your persona (the 'self' user).[/dim]")
        console.print()

        self_inputs = persona_input_prompts(is_self=True)
        self_persona = create_persona_from_input(self_inputs, is_self=True)

        console.print()
        console.print("[green]Self persona created![/green]")
    else:
        console.print("[dim]Skipping self persona creation (using existing).[/dim]")
    console.print()

    console.print("[bold]Step 2: Create Contact Personas[/bold]")
    console.print("[dim]Now add people you'll be having conversations with.[/dim]")
    console.print()

    contact_personas: list[Persona] = []

    while True:
        console.print(f"[dim]Creating contact #{len(contact_personas) + 1}[/dim]")
        inputs = persona_input_prompts(is_self=False)
        persona = create_persona_from_input(inputs, is_self=False)
        contact_personas.append(persona)

        console.print(f"[green]Created: {persona.name}[/green]")
        console.print()

        if not confirm_prompt("Add another contact?", default=len(contact_personas) < 2):
            break

    all_personas = [self_persona] + contact_personas

    console.print()
    console.print(persona_table(all_personas, title="Your Personas"))
    console.print()

    if not confirm_prompt("Save these personas and continue?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return None

    with PersonaStorage() as storage:
        if not append_mode:
            storage.create_many(all_personas)
        else:
            existing_self = storage.get_self()
            if not existing_self:
                storage.create(self_persona)
            for contact in contact_personas:
                storage.create(contact)
        console.print(f"[green]Saved {len(all_personas)} personas.[/green]")

    console.print()
    console.print("[bold]Step 3: Conversation Generation[/bold]")
    console.print()

    simulation_type = simulation_type_prompt()

    message_count = int_prompt(
        "Messages per conversation",
        default=DEFAULT_MESSAGE_COUNT,
        min_val=10,
        max_val=1000,
    )

    console.print()
    console.print("[dim]Checking LLM provider availability...[/dim]")

    provider = get_provider_with_preference(console)
    if provider is None:
        return None

    conversations_to_generate: list[tuple[Persona, str | None]] = []

    if simulation_type == "curated":
        console.print()
        console.print("[dim]Select which contacts to have conversations with:[/dim]")
        selected = select_personas_prompt(contact_personas, "Choose contacts for conversations")

        if not selected:
            console.print("[yellow]No contacts selected. Cancelled.[/yellow]")
            return None

        for contact in selected:
            console.print(f"\n[dim]Topic for conversation with {contact.name}:[/dim]")
            seed = conversation_seed_prompt()
            conversations_to_generate.append((contact, seed))
    else:
        for contact in contact_personas:
            conversations_to_generate.append((contact, None))

    start_time, end_time = get_default_time_range()

    console.print()
    mode_text = "Appending" if append_mode else "Generating"
    console.print(f"[dim]{mode_text} {len(conversations_to_generate)} conversation(s)...[/dim]")
    console.print()

    total_time_start = time.monotonic()
    all_messages: list[TimestampedMessage] = []
    conversation_count = 0
    last_provider_name = provider.name

    with DatabaseBuilder(output_path, append=append_mode) as builder:
        generator = ConversationGenerator(ProviderManager())

        with create_generation_progress() as progress:
            for contact, seed in conversations_to_generate:
                task_desc = f"Conversation with {contact.name}"
                task = progress.add_task(task_desc, total=message_count, phase="Starting...")

                config = ConversationConfig(
                    name=f"Chat with {contact.name}",
                    participants=[self_persona.id, contact.id],
                    chat_type=ChatType.DIRECT,
                    service=ServiceType.IMESSAGE,
                    message_count_target=message_count,
                    time_range_start=start_time,
                    time_range_end=end_time,
                    seed=seed,
                )

                callback = create_progress_callback(progress, task)

                try:
                    result: GenerationResult = asyncio.run(
                        generator.generate_to_database(
                            personas=[self_persona, contact],
                            config=config,
                            builder=builder,
                            progress_callback=callback,
                        )
                    )
                    all_messages.extend(result.messages)
                    conversation_count += 1
                    last_provider_name = result.llm_provider_used

                    progress.update(task, completed=message_count, phase="Done")
                except Exception as e:
                    progress.update(task, description=f"[red]Failed: {contact.name}[/red]")
                    console.print(
                        f"[red]Error generating conversation with {contact.name}: {e}[/red]"
                    )

    total_time = time.monotonic() - total_time_start

    addressbook_path = get_addressbook_path(output_path)
    with AddressBookBuilder(addressbook_path) as ab_builder:
        ab_builder.add_all_personas(all_personas)

    console.print()

    if all_messages:
        persona_map = {p.id: p for p in all_personas}
        console.print(message_preview_table(all_messages, persona_map, max_messages=15))
        console.print()

    console.print(
        generation_stats_table(
            total_messages=len(all_messages),
            total_conversations=conversation_count,
            total_time=total_time,
            provider=last_provider_name,
            output_path=output_path,
        )
    )

    console.print()
    console.print(
        Panel(
            f"[green]iMessage database:[/green] [blue]{output_path.absolute()}[/blue]\n"
            f"[green]AddressBook database:[/green] [blue]{addressbook_path.absolute()}[/blue]\n\n"
            "[dim]You can use these databases with imessage-exporter or BRB.[/dim]",
            title="Complete",
            border_style="green",
        )
    )

    return output_path
