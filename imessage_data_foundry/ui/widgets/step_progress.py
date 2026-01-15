"""Step progress bar widget - visual dots showing wizard progress."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static

from imessage_data_foundry.ui.state import WIZARD_STEPS


class StepProgressBar(Widget):
    """Visual step indicator with dots showing wizard progress (iOS setup style)."""

    current_step = reactive(1)

    def __init__(self, screen_id: str) -> None:
        super().__init__()
        self.screen_id = screen_id
        self._step_info = self._get_step_info()
        self.current_step = self._step_info[0]

    def _get_step_info(self) -> tuple[int, int, str]:
        for screen, title, step in WIZARD_STEPS:
            if screen == self.screen_id:
                return (step, len(WIZARD_STEPS), title)
        return (1, len(WIZARD_STEPS), "")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._render_dots(), id="step-dots", classes="step-dots")
            yield Label(self._step_info[2], id="step-title", classes="step-title")

    def _render_dots(self) -> str:
        step, total, _ = self._step_info
        dots = []
        for i in range(1, total + 1):
            if i < step:
                dots.append("[#34C759]●[/]")
            elif i == step:
                dots.append("[#007AFF]●[/]")
            else:
                dots.append("[#8E8E93]○[/]")
        return "  ".join(dots)

    def watch_current_step(self, _step: int) -> None:
        try:
            dots = self.query_one("#step-dots", Static)
            dots.update(self._render_dots())
        except Exception:
            pass
