"""Animated spinner widget - loading indicator."""

from __future__ import annotations

from textual.timer import Timer
from textual.widget import Widget


class AnimatedSpinner(Widget):
    """Apple-style animated loading spinner."""

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(
        self,
        text: str = "",
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.text = text
        self._frame = 0
        self._timer: Timer | None = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(1 / 12, self._advance_frame)

    def on_unmount(self) -> None:
        if self._timer:
            self._timer.stop()

    def _advance_frame(self) -> None:
        self._frame = (self._frame + 1) % len(self.SPINNER_FRAMES)
        self.refresh()

    def render(self) -> str:
        spinner = self.SPINNER_FRAMES[self._frame]
        if self.text:
            return f"[#007AFF]{spinner}[/] {self.text}"
        return f"[#007AFF]{spinner}[/]"

    def update_text(self, text: str) -> None:
        self.text = text
        self.refresh()
