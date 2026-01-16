import argparse
import sys
from pathlib import Path

from rich.console import Console

import imessage_data_foundry.cli.utils as cli_utils
from imessage_data_foundry import __version__
from imessage_data_foundry.cli.menu import run_menu_loop


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="imessage-data-foundry",
        description="Generate realistic, schema-accurate iMessage databases for testing and development",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PATH",
        help="Output path for generated chat.db (default: ./output/chat.db)",
    )
    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    console = Console()

    if args.output:
        cli_utils.DEFAULT_OUTPUT_PATH = args.output

    try:
        run_menu_loop(console)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
