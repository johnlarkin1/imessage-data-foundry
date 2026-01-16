from rich.console import Console

from imessage_data_foundry.cli.components.banner import show_welcome
from imessage_data_foundry.cli.components.prompts import main_menu_prompt
from imessage_data_foundry.cli.flows.guided import run_guided
from imessage_data_foundry.cli.flows.manage import run_manage
from imessage_data_foundry.cli.flows.quick_start import run_quick_start
from imessage_data_foundry.cli.flows.settings import run_settings


def run_menu_loop(console: Console) -> None:
    show_welcome(console)

    while True:
        choice = main_menu_prompt()

        if choice == "quick_start":
            run_quick_start(console)
            console.print()
        elif choice == "guided":
            run_guided(console)
            console.print()
        elif choice == "manage":
            run_manage(console)
            console.print()
        elif choice == "settings":
            run_settings(console)
            console.print()
        elif choice == "exit":
            console.print("[green]Goodbye![/green]")
            break
