import asyncio

from rich.console import Console
from rich.panel import Panel

from imessage_data_foundry.cli.components.prompts import confirm_prompt, provider_select_prompt
from imessage_data_foundry.llm.manager import ProviderManager
from imessage_data_foundry.settings.storage import SettingsStorage


def run_settings(console: Console) -> None:
    console.print()
    console.print(Panel("[bold magenta]Settings[/bold magenta]", border_style="magenta"))
    console.print()

    with SettingsStorage() as storage:
        current_provider = storage.get_provider()

    manager = ProviderManager()
    all_providers = asyncio.run(manager.list_all_providers())
    available = [(ptype, name) for ptype, name, is_avail, _ in all_providers if is_avail]
    unavailable = [
        (ptype, name, reason) for ptype, name, is_avail, reason in all_providers if not is_avail
    ]

    if current_provider:
        current_name = next(
            (name for ptype, name in available if ptype == current_provider),
            current_provider.value,
        )
        console.print(f"[dim]Current provider: {current_name}[/dim]")
    else:
        console.print("[dim]No provider configured yet.[/dim]")

    console.print()
    if available:
        console.print("[dim]Available providers:[/dim]")
        for ptype, name in available:
            marker = " [green](current)[/green]" if ptype == current_provider else ""
            console.print(f"  [green]✓[/green] {name}{marker}")
    else:
        console.print("[dim]Available providers:[/dim] [yellow]None[/yellow]")

    if unavailable:
        console.print()
        console.print("[dim]Unavailable providers:[/dim]")
        for _ptype, name, reason in unavailable:
            console.print(f"  [red]✗[/red] {name} [dim]({reason})[/dim]")
    console.print()

    if not available:
        console.print(
            Panel(
                "[yellow]To enable more providers:[/yellow]\n"
                "  • OpenAI: Set OPENAI_API_KEY environment variable\n"
                "  • Anthropic: Set ANTHROPIC_API_KEY environment variable\n"
                "  • Local: Install mlx-lm (pip install mlx-lm)",
                border_style="yellow",
            )
        )
        return

    if not confirm_prompt("Change LLM provider?", default=current_provider is None):
        return

    selected = provider_select_prompt(available, current_provider)

    with SettingsStorage() as storage:
        storage.set_provider(selected)

    selected_name = next(name for ptype, name in available if ptype == selected)
    console.print(f"[green]Provider set to: {selected_name}[/green]")
