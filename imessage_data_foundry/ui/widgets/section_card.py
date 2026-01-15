"""Section card widget - rounded container for grouping content."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label


class SectionCard(Widget):
    """Rounded card container with title for grouping related content.

    Use as a context manager to add children:
        with SectionCard("Title"):
            yield SelectionCard(...)
    """

    def __init__(
        self,
        title: str,
        *children: Widget,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._title = title
        self._pending_children = list(children)

    def compose(self) -> ComposeResult:
        yield Label(self._title, classes="card-title")
        yield Vertical(*self._pending_children, classes="card-content", id="section-content")

    def compose_add_child(self, widget: Widget) -> None:
        """Handle children added via context manager."""
        self._pending_children.append(widget)
