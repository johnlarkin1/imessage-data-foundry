"""Avatar circle widget - displays initials in a colored circle."""

from __future__ import annotations

from textual.widget import Widget


class AvatarCircle(Widget):
    """Circular avatar showing initials with background color."""

    AVATAR_COLORS = [
        "#FF6B6B",
        "#4ECDC4",
        "#45B7D1",
        "#96CEB4",
        "#FFEAA7",
        "#DDA0DD",
        "#98D8C8",
        "#F7DC6F",
        "#BB8FCE",
        "#85C1E9",
    ]

    def __init__(
        self,
        name: str,
        is_self: bool = False,
        small: bool = False,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.persona_name = name
        self.is_self = is_self
        self._initials = self._get_initials(name)
        self._color = self._get_color(name)
        if small:
            self.add_class("small")

    def _get_initials(self, name: str) -> str:
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[:2].upper() if len(name) >= 2 else name.upper()

    def _get_color(self, name: str) -> str:
        if self.is_self:
            return "#007AFF"
        return self.AVATAR_COLORS[hash(name) % len(self.AVATAR_COLORS)]

    def render(self) -> str:
        return f"[{self._color} bold]({self._initials})[/]"
