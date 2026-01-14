"""Base screen with common functionality for wizard navigation."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Label, Static

from imessage_data_foundry.ui.state import get_step_info

if TYPE_CHECKING:
    from imessage_data_foundry.ui.state import AppState


class StepIndicator(Static):
    """Widget showing current step in the wizard."""

    DEFAULT_CSS = """
    StepIndicator {
        dock: top;
        height: 3;
        content-align: center middle;
        background: $primary-darken-2;
        color: $text;
        padding: 0 2;
    }
    """

    def __init__(self, screen_id: str) -> None:
        super().__init__()
        self.screen_id = screen_id

    def compose(self) -> ComposeResult:
        step, total, title = get_step_info(self.screen_id)
        yield Label(f"Step {step} of {total}: {title}", id="step-label")


class WizardScreen(Screen):
    """Base class for wizard screens with common navigation patterns.

    Subclasses should:
    - Set SCREEN_ID class variable
    - Override body() to return screen-specific content
    - Override action_next() to handle forward navigation
    - Optionally override action_back() for custom back behavior
    """

    SCREEN_ID: ClassVar[str] = ""

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    @property
    def state(self) -> AppState:
        """Access the shared application state."""
        return self.app.state  # type: ignore[attr-defined]

    def compose(self) -> ComposeResult:
        yield StepIndicator(self.SCREEN_ID)
        with Container(id="screen-body"):
            yield from self.body()
        yield Footer()

    def body(self) -> ComposeResult:
        """Override to provide screen-specific content."""
        yield Label("Override body() in subclass")

    def action_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_next(self) -> None:
        """Proceed to the next screen. Override in subclass."""


class NavigationBar(Horizontal):
    """Bottom navigation bar with Back/Next buttons."""

    DEFAULT_CSS = """
    NavigationBar {
        dock: bottom;
        height: 3;
        padding: 0 2;
        align: right middle;
    }

    NavigationBar Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        show_back: bool = True,
        show_next: bool = True,
        next_label: str = "Next",
        next_disabled: bool = False,
    ) -> None:
        super().__init__()
        self.show_back = show_back
        self.show_next = show_next
        self.next_label = next_label
        self.next_disabled = next_disabled

    def compose(self) -> ComposeResult:
        from textual.widgets import Button

        if self.show_back:
            yield Button("Back", id="nav-back", variant="default")
        if self.show_next:
            yield Button(
                self.next_label,
                id="nav-next",
                variant="primary",
                disabled=self.next_disabled,
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "nav-back":
            self.screen.action_back()  # type: ignore[attr-defined]
        elif event.button.id == "nav-next":
            self.screen.action_next()  # type: ignore[attr-defined]
