import asyncio

from rich.console import Console
from rich.panel import Panel

from imessage_data_foundry.cli.components.prompts import provider_select_prompt
from imessage_data_foundry.llm.base import LLMProvider
from imessage_data_foundry.llm.manager import ProviderManager, ProviderNotAvailableError
from imessage_data_foundry.settings.storage import SettingsStorage


def get_provider_with_preference(console: Console) -> LLMProvider | None:
    with SettingsStorage() as storage:
        stored_provider = storage.get_provider()

    manager = ProviderManager()

    if stored_provider:
        try:
            provider = asyncio.run(manager.get_provider(preferred=stored_provider))
            console.print(f"[green]Using LLM provider: {provider.name}[/green]")
            return provider
        except ProviderNotAvailableError:
            console.print(
                f"[yellow]Previously selected provider ({stored_provider.value}) "
                "is no longer available.[/yellow]"
            )

    available = asyncio.run(manager.list_available_providers())

    if not available:
        console.print(
            Panel(
                "[red]No LLM providers available.[/red]\n\n"
                "Options:\n"
                "  1. Install mlx-lm for local inference: pip install mlx-lm\n"
                "  2. Set OPENAI_API_KEY environment variable\n"
                "  3. Set ANTHROPIC_API_KEY environment variable",
                border_style="red",
            )
        )
        return None

    if len(available) == 1:
        ptype, name = available[0]
        with SettingsStorage() as storage:
            storage.set_provider(ptype)
        provider = asyncio.run(manager.get_provider_by_type(ptype))
        console.print(f"[green]Using LLM provider: {name}[/green]")
        return provider

    console.print()
    console.print("[dim]Multiple LLM providers available. Please select one:[/dim]")
    selected = provider_select_prompt(available)

    with SettingsStorage() as storage:
        storage.set_provider(selected)

    provider = asyncio.run(manager.get_provider_by_type(selected))
    console.print(f"[green]Using LLM provider: {provider.name}[/green]")
    return provider
