"""TextArea with placeholder text support."""

from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import TextArea


class PlaceholderTextArea(TextArea):
    """TextArea that displays placeholder when empty."""

    placeholder = reactive("")

    def __init__(
        self,
        text: str = "",
        placeholder: str = "",
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(text, id=id, classes=classes)
        self.placeholder = placeholder
        self._showing_placeholder = False
        if not text and placeholder:
            self._show_placeholder()

    def _show_placeholder(self) -> None:
        if not self._showing_placeholder and not self.text:
            self._showing_placeholder = True
            self.load_text(self.placeholder)
            self.add_class("placeholder-visible")

    def _hide_placeholder(self) -> None:
        if self._showing_placeholder:
            self._showing_placeholder = False
            self.clear()
            self.remove_class("placeholder-visible")

    def on_focus(self) -> None:
        if self._showing_placeholder:
            self._hide_placeholder()

    def on_blur(self) -> None:
        if not self.text:
            self._show_placeholder()

    @property
    def value(self) -> str:
        """Return empty string if showing placeholder."""
        if self._showing_placeholder:
            return ""
        return self.text
