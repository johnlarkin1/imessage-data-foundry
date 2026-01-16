import time

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

BANNER_ART = r"""
 _   __  __                                   ____        _
(_) |  \/  | ___  ___ ___  __ _  __ _  ___   |  _ \  __ _| |_ __ _
| | | |\/| |/ _ \/ __/ __|/ _` |/ _` |/ _ \  | | | |/ _` | __/ _` |
| | | |  | |  __/\__ \__ \ (_| | (_| |  __/  | |_| | (_| | || (_| |
|_| |_|  |_|\___||___/___/\__,_|\__, |\___|  |____/ \__,_|\__\__,_|
                                |___/
              _____                      _
             |  ___|__  _   _ _ __   __| |_ __ _   _
             | |_ / _ \| | | | '_ \ / _` | '__| | | |
             |  _| (_) | |_| | | | | (_| | |  | |_| |
             |_|  \___/ \__,_|_| |_|\__,_|_|   \__, |
                                               |___/
"""


def _pad_lines_to_equal_width(text: str) -> str:
    lines = text.strip().split("\n")
    max_width = max(len(line) for line in lines)
    padded = [line.ljust(max_width) for line in lines]
    return "\n".join(padded)


def show_welcome(console: Console, animate: bool = True) -> None:
    console.clear()
    console.print()

    padded_art = _pad_lines_to_equal_width(BANNER_ART)

    if animate:
        lines = padded_art.split("\n")
        for line in lines:
            styled = Text(line, style="bold cyan")
            console.print(Align.center(styled))
            time.sleep(0.03)
        time.sleep(0.1)
    else:
        banner_text = Text(padded_art, style="bold cyan")
        console.print(Align.center(banner_text))

    console.print()

    title = Text()
    title.append("iMessage ", style="bold cyan")
    title.append("Data ", style="bold blue")
    title.append("Foundry", style="bold magenta")
    console.print(Align.center(title))

    console.print()
    tagline = Text("Generate realistic iMessage databases for testing", style="italic dim")
    console.print(Align.center(tagline))
    console.print()

    options = Text()
    options.append("Quick Start", style="green bold")
    options.append(" - Auto-generate personas and conversations\n", style="dim")
    options.append("Guided", style="blue bold")
    options.append(" - Create personas manually with full control\n", style="dim")
    options.append("Manage", style="yellow bold")
    options.append(" - Edit or delete existing personas", style="dim")

    console.print(Panel(options, title="Options", border_style="dim"))
    console.print()
