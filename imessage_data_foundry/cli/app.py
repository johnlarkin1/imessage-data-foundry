from rich.console import Console

from imessage_data_foundry.cli.menu import run_menu_loop


def main() -> None:
    console = Console()
    try:
        run_menu_loop(console)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise


if __name__ == "__main__":
    main()
