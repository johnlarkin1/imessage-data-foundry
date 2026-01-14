"""Entry point for running as a module: python -m imessage_data_foundry."""

import sys


def main() -> None:
    """Run the iMessage Data Foundry application.

    Dispatches to CLI if arguments provided, otherwise launches TUI.
    """
    if len(sys.argv) > 1:
        from imessage_data_foundry.cli import cli

        cli()
    else:
        from imessage_data_foundry.app import main as tui_main

        tui_main()


if __name__ == "__main__":
    main()
