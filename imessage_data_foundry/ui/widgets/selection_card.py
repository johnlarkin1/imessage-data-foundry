"""Selection card widget - selectable card for option selection."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label


class SelectionCard(Widget):
    """Selectable card widget for option selection (replaces RadioButton)."""

    can_focus = True

    selected = reactive(False)

    class Selected(Message):
        """Posted when the card is selected."""

        def __init__(self, card: SelectionCard) -> None:
            self.card = card
            self.value = card.value
            super().__init__()

    def __init__(
        self,
        label: str,
        description: str = "",
        icon: str = "",
        value: str = "",
        selected: bool = False,
        disabled: bool = False,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.label_text = label
        self.description = description
        self.icon = icon
        self.value = value or label.lower().replace(" ", "-")
        self.selected = selected
        self._disabled = disabled
        if disabled:
            self.add_class("disabled")
            self.can_focus = False

    def compose(self) -> ComposeResult:
        with Horizontal(classes="card-row"):
            if self.icon:
                yield Label(self.icon, classes="card-icon")
            with Vertical(classes="card-info"):
                yield Label(self.label_text, classes="card-label")
                if self.description:
                    yield Label(self.description, classes="card-description")
            status = "[#007AFF]●[/]" if self.selected else "[#8E8E93]○[/]"
            yield Label(status, classes="card-status", id=f"{self.id}-status" if self.id else None)

    def watch_selected(self, selected: bool) -> None:
        self.set_class(selected, "selected")
        try:
            status_id = f"#{self.id}-status" if self.id else ".card-status"
            status = self.query_one(status_id, Label)
            status.update("[#007AFF]●[/]" if selected else "[#8E8E93]○[/]")
        except Exception:
            pass

    def on_click(self) -> None:
        if not self._disabled:
            self.post_message(self.Selected(self))

    def action_select(self) -> None:
        if not self._disabled:
            self.post_message(self.Selected(self))

    BINDINGS = [("enter", "select", "Select"), ("space", "select", "Select")]
