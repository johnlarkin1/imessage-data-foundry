import asyncio
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from imessage_data_foundry.cli.components.progress import (
    create_generation_progress,
    create_progress_callback,
    create_simple_progress,
)
from imessage_data_foundry.cli.components.prompts import confirm_prompt, text_prompt
from imessage_data_foundry.cli.components.tables import (
    generation_stats_table,
    message_preview_table,
    persona_table,
)
from imessage_data_foundry.cli.provider_helper import get_provider_with_preference
from imessage_data_foundry.cli.utils import (
    DEFAULT_MESSAGE_COUNT,
    DEFAULT_PERSONA_COUNT,
    DatabaseExistsAction,
    create_self_persona,
    ensure_output_dir,
    generated_to_full_persona,
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
from imessage_data_foundry.personas.models import ChatType, ConversationConfig, ServiceType
from imessage_data_foundry.personas.storage import PersonaStorage


def run_quick_start(console: Console) -> Path | None:
    console.print()
    console.print(Panel("[bold cyan]Quick Start Mode[/bold cyan]", border_style="cyan"))
    console.print()

    console.print("[dim]This will auto-generate personas and conversations using AI.[/dim]")
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

    console.print()
    if self_persona is None:
        your_name = text_prompt("What's your name?", default="Me", validate=True)
    else:
        your_name = self_persona.name

    console.print()
    console.print("[dim]Checking LLM provider availability...[/dim]")

    provider = get_provider_with_preference(console)
    if provider is None:
        return None

    console.print()
    console.print(f"[dim]Generating {DEFAULT_PERSONA_COUNT} contact personas...[/dim]")

    with create_simple_progress() as progress:
        task = progress.add_task("Generating personas...", total=DEFAULT_PERSONA_COUNT)

        try:
            generated_personas = asyncio.run(
                provider.generate_personas(count=DEFAULT_PERSONA_COUNT)
            )
            progress.update(task, completed=DEFAULT_PERSONA_COUNT)
        except Exception as e:
            console.print(Panel(f"[red]Failed to generate personas:[/red] {e}", border_style="red"))
            return None

    if self_persona is None:
        self_persona = create_self_persona(name=your_name)
    contact_personas = [generated_to_full_persona(gp) for gp in generated_personas]
    all_personas = [self_persona] + contact_personas

    console.print()
    console.print(persona_table(all_personas, title="Generated Personas"))
    console.print()

    if not confirm_prompt("Proceed with these personas?", default=True):
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
        console.print(f"[green]Saved {len(all_personas)} personas to storage.[/green]")

    start_time, end_time = get_default_time_range()

    console.print()
    mode_text = "Appending to" if append_mode else "Generating"
    console.print(
        f"[dim]{mode_text} conversations ({DEFAULT_MESSAGE_COUNT} messages each)...[/dim]"
    )
    console.print()

    total_time_start = time.monotonic()
    all_messages: list[TimestampedMessage] = []
    conversation_count = 0
    last_provider_name = provider.name

    with DatabaseBuilder(output_path, append=append_mode) as builder:
        generator = ConversationGenerator(ProviderManager())

        with create_generation_progress() as progress:
            for contact in contact_personas:
                task_desc = f"Conversation with {contact.name}"
                task = progress.add_task(
                    task_desc, total=DEFAULT_MESSAGE_COUNT, phase="Starting..."
                )

                config = ConversationConfig(
                    name=f"Chat with {contact.name}",
                    participants=[self_persona.id, contact.id],
                    chat_type=ChatType.DIRECT,
                    service=ServiceType.IMESSAGE,
                    message_count_target=DEFAULT_MESSAGE_COUNT,
                    time_range_start=start_time,
                    time_range_end=end_time,
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

                    progress.update(task, completed=DEFAULT_MESSAGE_COUNT, phase="Done")
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
