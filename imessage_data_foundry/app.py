"""Main TUI application entry point."""

from pathlib import Path

from textual.app import App

from imessage_data_foundry.ui.screens.welcome import WelcomeScreen
from imessage_data_foundry.ui.state import AppState


class FoundryApp(App):
    """iMessage Data Foundry TUI application."""

    TITLE = "iMessage Data Foundry"
    CSS_PATH = Path(__file__).parent / "ui" / "styles.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.state = AppState()

    def on_mount(self) -> None:
        self.push_screen(WelcomeScreen())


def main() -> None:
    """Run the iMessage Data Foundry TUI application."""
    app = FoundryApp()
    app.run()


if __name__ == "__main__":
    main()
