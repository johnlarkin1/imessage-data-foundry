"""Utilities for robust enum parsing from LLM responses."""

from enum import Enum
from typing import TypeVar

T = TypeVar("T", bound=Enum)


def parse_enum(value: str, enum_class: type[T], default: T) -> T:
    """Parse a string value to an enum with fuzzy matching and fallback.

    Handles LLM responses that may include extra text like:
    - "heavy (e.g., smiling faces, hearts, stars)" -> EmojiUsage.HEAVY
    - "INSTANT" -> ResponseTime.INSTANT (case insensitive)
    """
    value_lower = value.lower().strip()

    for member in enum_class:
        if member.value.lower() == value_lower:
            return member

    for member in enum_class:
        if value_lower.startswith(member.value.lower()):
            return member

    for member in enum_class:
        if member.value.lower() in value_lower:
            return member

    return default
