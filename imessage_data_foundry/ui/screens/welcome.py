"""Welcome screen - entry point for the TUI wizard."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Container, Vertical
from textual.widgets import Button, Label, Static

from imessage_data_foundry.ui.screens.base import WizardScreen
from imessage_data_foundry.ui.state import Screen

LOGO = r"""
    ___ __  __
   (_)  \/  |___ ___ ___  __ _ __ _ ___
   | | |\/| / -_|_-<(_-< / _` / _` / -_)
   |_|_|  |_\___/__//__/ \__,_\__, \___|
                              |___/
     ___       _          ___                  _
    |   \ __ _| |_ __ _  | __|__ _  _ _ _  __| |_ _ _  _
    | |) / _` |  _/ _` | | _/ _ \ || | ' \/ _` | '_| || |
    |___/\__,_|\__\__,_| |_|\___/\_,_|_||_\__,_|_|  \_, |
                                                    |__/
"""


class WelcomeScreen(WizardScreen):
    """Welcome screen with app overview and quick actions."""

    SCREEN_ID = Screen.WELCOME

    def body(self) -> ComposeResult:
        with Center(), Vertical(id="welcome-content"):
            yield Static(LOGO, id="logo")
            yield Label(
                "Generate realistic iMessage databases for testing and development",
                id="tagline",
            )
            yield Container(id="spacer")
            with Center(id="button-row"):
                yield Button(
                    "Start Wizard",
                    id="start-wizard",
                    variant="primary",
                )
                yield Button(
                    "Manage Personas",
                    id="manage-personas",
                    variant="default",
                )
            yield Container(id="spacer2")
            yield Label(
                "Press [bold]q[/bold] to quit | [bold]Enter[/bold] to start",
                id="hint",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-wizard":
            self.action_next()
        elif event.button.id == "manage-personas":
            from imessage_data_foundry.ui.screens.personas import PersonasScreen

            self.app.push_screen(PersonasScreen())

    def action_next(self) -> None:
        from imessage_data_foundry.ui.screens.config import ConfigScreen

        self.app.push_screen(ConfigScreen())

    def action_back(self) -> None:
        pass
