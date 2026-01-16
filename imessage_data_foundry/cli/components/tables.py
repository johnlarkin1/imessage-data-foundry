from pathlib import Path

from rich import box
from rich.table import Table

from imessage_data_foundry.conversations.generator import GenerationResult, TimestampedMessage
from imessage_data_foundry.personas.models import Persona
from imessage_data_foundry.utils.apple_time import apple_ns_to_datetime


def persona_table(personas: list[Persona], title: str = "Personas") -> Table:
    table = Table(title=title, box=box.ROUNDED)
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", style="cyan")
    table.add_column("Identifier", style="blue")
    table.add_column("Relationship", style="yellow")
    table.add_column("Topics", style="green")
    table.add_column("Style", style="magenta")
    table.add_column("Self", style="bold", width=4)

    for i, p in enumerate(personas, 1):
        is_self = "[green]Yes[/green]" if p.is_self else "[dim]No[/dim]"
        topics = ", ".join(p.topics_of_interest[:3]) if p.topics_of_interest else "[dim]—[/dim]"
        if len(topics) > 30:
            topics = topics[:27] + "..."
        table.add_row(
            str(i),
            p.name,
            p.display_identifier,
            p.relationship,
            topics,
            p.writing_style[:15] + "..." if len(p.writing_style) > 15 else p.writing_style,
            is_self,
        )

    return table


def persona_detail_table(persona: Persona) -> Table:
    table = Table(title=f"Persona: {persona.name}", box=box.ROUNDED, show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Name", persona.name)
    table.add_row("Identifier", persona.display_identifier)
    table.add_row("Relationship", persona.relationship)
    table.add_row("Personality", persona.personality or "[dim]Not set[/dim]")
    table.add_row("Writing Style", persona.writing_style)
    table.add_row("Communication", persona.communication_frequency.value)
    table.add_row("Response Time", persona.typical_response_time.value)
    table.add_row("Emoji Usage", persona.emoji_usage.value)
    table.add_row("Vocabulary", persona.vocabulary_level.value)
    table.add_row("Topics", ", ".join(persona.topics_of_interest) or "[dim]None[/dim]")
    table.add_row("Is Self", "[green]Yes[/green]" if persona.is_self else "[dim]No[/dim]")

    return table


def message_preview_table(
    messages: list[TimestampedMessage],
    personas: dict[str, Persona],
    max_messages: int = 10,
) -> Table:
    table = Table(title="Message Preview", box=box.ROUNDED)
    table.add_column("Time", style="dim", width=8)
    table.add_column("Sender", style="cyan", width=12)
    table.add_column("Message", style="white")

    display_messages = messages[:max_messages]

    for tm in display_messages:
        msg = tm.message
        dt = apple_ns_to_datetime(tm.timestamp)
        time_str = dt.strftime("%H:%M")

        if msg.is_from_me:
            sender = "[green]You[/green]"
        else:
            persona = personas.get(msg.sender_id)
            sender = persona.name if persona else msg.sender_id[:8]

        text = msg.text
        if len(text) > 60:
            text = text[:57] + "..."

        table.add_row(time_str, sender, text)

    if len(messages) > max_messages:
        table.add_row("...", f"[dim]+{len(messages) - max_messages} more[/dim]", "")

    return table


def summary_table(
    result: GenerationResult,
    output_path: Path,
    conversation_count: int = 1,
) -> Table:
    table = Table(title="Generation Summary", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Messages Generated", f"[green]{len(result.messages)}[/green]")
    table.add_row("Conversations", str(conversation_count))
    table.add_row("Generation Time", f"{result.generation_time_seconds:.2f}s")
    table.add_row("LLM Provider", result.llm_provider_used)
    table.add_row("Output Path", f"[blue]{output_path}[/blue]")

    return table


def generation_stats_table(
    total_messages: int,
    total_conversations: int,
    total_time: float,
    provider: str,
    output_path: Path,
) -> Table:
    table = Table(title="Generation Complete", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")

    table.add_row("Total Messages", str(total_messages))
    table.add_row("Conversations", str(total_conversations))
    table.add_row("Total Time", f"{total_time:.2f}s")
    table.add_row("LLM Provider", provider)
    table.add_row("Database", f"[blue]{output_path}[/blue]")

    return table
