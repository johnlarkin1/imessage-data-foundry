"""Command-line interface for iMessage Data Foundry."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from imessage_data_foundry.conversations.generator import (
    ConversationGenerator,
    GenerationProgress,
)
from imessage_data_foundry.db.builder import DatabaseBuilder
from imessage_data_foundry.db.schema.base import SchemaVersion
from imessage_data_foundry.llm.config import ProviderType
from imessage_data_foundry.llm.manager import ProviderManager, ProviderNotAvailableError
from imessage_data_foundry.personas.models import (
    ChatType,
    CommunicationFrequency,
    ConversationConfig,
    EmojiUsage,
    IdentifierType,
    Persona,
    ResponseTime,
    ServiceType,
    VocabularyLevel,
)
from imessage_data_foundry.personas.storage import PersonaStorage

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="iMessage Data Foundry")
def cli() -> None:
    """iMessage Data Foundry - Generate realistic iMessage databases."""


@cli.command("list-providers")
def list_providers() -> None:
    """List available LLM providers."""

    async def _list() -> list[tuple[ProviderType, str]]:
        manager = ProviderManager()
        return await manager.list_available_providers()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Checking providers...", total=None)
        providers = asyncio.run(_list())

    if not providers:
        console.print("[yellow]No LLM providers available.[/yellow]")
        console.print("\nTo enable providers:")
        console.print("  - Local: Install mlx-lm (Apple Silicon only)")
        console.print("  - OpenAI: Set OPENAI_API_KEY environment variable")
        console.print("  - Anthropic: Set ANTHROPIC_API_KEY environment variable")
        return

    table = Table(title="Available LLM Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Type", style="green")

    for provider_type, name in providers:
        table.add_row(name, provider_type.value)

    console.print(table)


@cli.command("list-personas")
@click.option("--verbose", "-v", is_flag=True, help="Show all persona details")
def list_personas(verbose: bool) -> None:
    """List all saved personas."""
    with PersonaStorage() as storage:
        personas = storage.list_all()

    if not personas:
        console.print("[yellow]No personas found.[/yellow]")
        console.print(
            "Create one with: foundry create-persona --name 'Alice' --identifier '+15551234567'"
        )
        return

    table = Table(title=f"Personas ({len(personas)} total)")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Name", style="cyan")
    table.add_column("Identifier", style="green")
    table.add_column("Relationship", style="yellow")
    table.add_column("Self", style="magenta")

    if verbose:
        table.add_column("Personality", max_width=30)
        table.add_column("Style")

    for p in personas:
        row = [
            p.id[:8],
            p.name,
            p.display_identifier,
            p.relationship,
            "Yes" if p.is_self else "",
        ]
        if verbose:
            row.extend(
                [
                    p.personality[:30] + "..." if len(p.personality) > 30 else p.personality,
                    p.writing_style,
                ]
            )
        table.add_row(*row)

    console.print(table)


@cli.command("create-persona")
@click.option("--name", "-n", required=True, help="Persona name")
@click.option("--identifier", "-i", required=True, help="Phone number (E.164) or email")
@click.option("--identifier-type", type=click.Choice(["phone", "email"]), default="phone")
@click.option("--personality", "-p", default="", help="Personality description")
@click.option("--writing-style", default="casual", help="Writing style")
@click.option("--relationship", "-r", default="friend", help="Relationship to user")
@click.option(
    "--frequency",
    type=click.Choice(["high", "medium", "low"]),
    default="medium",
    help="Communication frequency",
)
@click.option(
    "--response-time",
    type=click.Choice(["instant", "minutes", "hours", "days"]),
    default="minutes",
)
@click.option(
    "--emoji-usage",
    type=click.Choice(["none", "light", "moderate", "heavy"]),
    default="light",
)
@click.option(
    "--vocabulary",
    type=click.Choice(["simple", "moderate", "sophisticated"]),
    default="moderate",
)
@click.option("--topics", "-t", multiple=True, help="Topics of interest (can specify multiple)")
@click.option("--is-self", is_flag=True, help="Mark as self (your persona)")
def create_persona(
    name: str,
    identifier: str,
    identifier_type: str,
    personality: str,
    writing_style: str,
    relationship: str,
    frequency: str,
    response_time: str,
    emoji_usage: str,
    vocabulary: str,
    topics: tuple[str, ...],
    is_self: bool,
) -> None:
    """Create a new persona manually."""
    persona = Persona(
        name=name,
        identifier=identifier,
        identifier_type=IdentifierType(identifier_type),
        personality=personality,
        writing_style=writing_style,
        relationship=relationship,
        communication_frequency=CommunicationFrequency(frequency),
        typical_response_time=ResponseTime(response_time),
        emoji_usage=EmojiUsage(emoji_usage),
        vocabulary_level=VocabularyLevel(vocabulary),
        topics_of_interest=list(topics),
        is_self=is_self,
    )

    with PersonaStorage() as storage:
        storage.create(persona)

    console.print(f"[green]Created persona:[/green] {name} ({persona.id[:8]})")
    console.print(f"  Identifier: {persona.display_identifier}")
    console.print(f"  Relationship: {relationship}")
    if is_self:
        console.print("  [magenta]Marked as self[/magenta]")


@cli.command("delete-persona")
@click.argument("persona_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def delete_persona(persona_id: str, force: bool) -> None:
    """Delete a persona by ID (can use partial ID)."""
    with PersonaStorage() as storage:
        personas = storage.list_all()

        matches = [p for p in personas if p.id.startswith(persona_id)]

        if not matches:
            console.print(f"[red]No persona found matching: {persona_id}[/red]")
            return

        if len(matches) > 1:
            console.print(f"[yellow]Multiple matches for '{persona_id}':[/yellow]")
            for p in matches:
                console.print(f"  {p.id[:8]} - {p.name}")
            console.print("Please be more specific.")
            return

        persona = matches[0]

        if not force and not click.confirm(f"Delete '{persona.name}' ({persona.id[:8]})?"):
            console.print("Cancelled.")
            return

        storage.delete(persona.id)
        console.print(f"[green]Deleted persona: {persona.name}[/green]")


@cli.command("generate")
@click.option(
    "--personas",
    "-p",
    required=True,
    help="Comma-separated persona IDs or partial IDs",
)
@click.option("--count", "-c", default=100, help="Number of messages to generate")
@click.option("--output", "-o", default="./output/chat.db", help="Output database path")
@click.option(
    "--version",
    type=click.Choice(["sonoma", "sequoia", "tahoe"]),
    default="sequoia",
    help="macOS schema version",
)
@click.option("--seed", "-s", help="Conversation topic/seed")
@click.option("--days", "-d", default=30, help="Time range in days (from now)")
@click.option(
    "--service",
    type=click.Choice(["iMessage", "SMS"]),
    default="iMessage",
)
def generate(
    personas: str,
    count: int,
    output: str,
    version: str,
    seed: str | None,
    days: int,
    service: str,
) -> None:
    """Generate a conversation and create database.

    Example:
        foundry generate --personas "abc123,def456" --count 200 --seed "planning a trip"
    """
    persona_ids = [p.strip() for p in personas.split(",")]

    with PersonaStorage() as storage:
        all_personas = storage.list_all()
        selected: list[Persona] = []

        for pid in persona_ids:
            matches = [p for p in all_personas if p.id.startswith(pid)]
            if not matches:
                console.print(f"[red]No persona found matching: {pid}[/red]")
                return
            if len(matches) > 1:
                console.print(f"[yellow]Ambiguous ID '{pid}', matches:[/yellow]")
                for p in matches:
                    console.print(f"  {p.id[:8]} - {p.name}")
                return
            selected.append(matches[0])

    if len(selected) < 2:
        console.print("[red]Need at least 2 personas for a conversation.[/red]")
        return

    self_personas = [p for p in selected if p.is_self]
    if not self_personas:
        console.print("[red]One persona must be marked as is_self=True[/red]")
        console.print("Use: foundry create-persona --name 'Me' --identifier '+1...' --is-self")
        return

    console.print("\n[bold]Generation Settings[/bold]")
    console.print(f"  Personas: {', '.join(p.name for p in selected)}")
    console.print(f"  Messages: {count}")
    console.print(f"  Output: {output}")
    console.print(f"  Schema: {version}")
    console.print(f"  Seed: {seed or '(none)'}")
    console.print()

    now = datetime.now(UTC)
    config = ConversationConfig(
        participants=[p.id for p in selected],
        chat_type=ChatType.DIRECT if len(selected) == 2 else ChatType.GROUP,
        message_count_target=count,
        time_range_start=now - timedelta(days=days),
        time_range_end=now,
        seed=seed,
        service=ServiceType(service),
    )

    async def run_generation() -> None:
        manager = ProviderManager()
        generator = ConversationGenerator(manager)

        schema_version = SchemaVersion(version.upper())
        output_path = Path(output)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Starting...", total=count)

            def on_progress(p: GenerationProgress) -> None:
                progress.update(
                    task,
                    completed=p.generated_messages,
                    description=f"{p.phase}: {p.generated_messages}/{p.total_messages}",
                )

            try:
                with DatabaseBuilder(output_path, version=schema_version) as builder:
                    result = await generator.generate_to_database(
                        personas=selected,
                        config=config,
                        builder=builder,
                        progress_callback=on_progress,
                    )

                console.print("\n[green]Generation complete![/green]")
                console.print(f"  Messages: {len(result.messages)}")
                console.print(f"  Chat ID: {result.chat_id}")
                console.print(f"  Time: {result.generation_time_seconds:.1f}s")
                console.print(f"  Provider: {result.llm_provider_used}")
                console.print(f"  Output: {output_path.absolute()}")

            except ProviderNotAvailableError as e:
                console.print(f"[red]No LLM provider available:[/red]\n{e}")

    asyncio.run(run_generation())


@cli.command("show-persona")
@click.argument("persona_id")
def show_persona(persona_id: str) -> None:
    """Show detailed information about a persona."""
    with PersonaStorage() as storage:
        personas = storage.list_all()
        matches = [p for p in personas if p.id.startswith(persona_id)]

        if not matches:
            console.print(f"[red]No persona found matching: {persona_id}[/red]")
            return

        if len(matches) > 1:
            console.print(f"[yellow]Multiple matches for '{persona_id}':[/yellow]")
            for p in matches:
                console.print(f"  {p.id[:8]} - {p.name}")
            return

        p = matches[0]

    console.print(f"\n[bold cyan]{p.name}[/bold cyan]")
    console.print(f"  ID: {p.id}")
    console.print(f"  Identifier: {p.display_identifier} ({p.identifier_type.value})")
    console.print(f"  Relationship: {p.relationship}")
    console.print(f"  Is Self: {'Yes' if p.is_self else 'No'}")
    console.print()
    console.print("[bold]Personality[/bold]")
    console.print(f"  {p.personality or '(not set)'}")
    console.print()
    console.print("[bold]Behavior[/bold]")
    console.print(f"  Writing Style: {p.writing_style}")
    console.print(f"  Communication: {p.communication_frequency.value}")
    console.print(f"  Response Time: {p.typical_response_time.value}")
    console.print(f"  Emoji Usage: {p.emoji_usage.value}")
    console.print(f"  Vocabulary: {p.vocabulary_level.value}")
    console.print()
    if p.topics_of_interest:
        console.print("[bold]Topics[/bold]")
        for topic in p.topics_of_interest:
            console.print(f"  - {topic}")
    console.print()
    console.print(f"[dim]Created: {p.created_at.strftime('%Y-%m-%d %H:%M')}[/dim]")
    console.print(f"[dim]Updated: {p.updated_at.strftime('%Y-%m-%d %H:%M')}[/dim]")


if __name__ == "__main__":
    cli()
