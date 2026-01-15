"""Tests for the enum parsing utility."""

from imessage_data_foundry.personas.models import (
    CommunicationFrequency,
    EmojiUsage,
    ResponseTime,
    VocabularyLevel,
)
from imessage_data_foundry.utils.enum_parsing import parse_enum


class TestParseEnum:
    def test_exact_match(self) -> None:
        assert parse_enum("heavy", EmojiUsage, EmojiUsage.LIGHT) == EmojiUsage.HEAVY
        assert parse_enum("light", EmojiUsage, EmojiUsage.MODERATE) == EmojiUsage.LIGHT
        assert parse_enum("none", EmojiUsage, EmojiUsage.LIGHT) == EmojiUsage.NONE

    def test_case_insensitive(self) -> None:
        assert parse_enum("HEAVY", EmojiUsage, EmojiUsage.LIGHT) == EmojiUsage.HEAVY
        assert parse_enum("Heavy", EmojiUsage, EmojiUsage.LIGHT) == EmojiUsage.HEAVY
        assert parse_enum("LIGHT", EmojiUsage, EmojiUsage.MODERATE) == EmojiUsage.LIGHT

    def test_prefix_match(self) -> None:
        result = parse_enum(
            "heavy (e.g., smiling faces, hearts, stars)",
            EmojiUsage,
            EmojiUsage.LIGHT,
        )
        assert result == EmojiUsage.HEAVY

        result = parse_enum(
            "moderate - uses emojis occasionally",
            EmojiUsage,
            EmojiUsage.LIGHT,
        )
        assert result == EmojiUsage.MODERATE

    def test_substring_match(self) -> None:
        result = parse_enum(
            "uses heavy emoji usage",
            EmojiUsage,
            EmojiUsage.LIGHT,
        )
        assert result == EmojiUsage.HEAVY

    def test_fallback_to_default(self) -> None:
        result = parse_enum("unknown_value", EmojiUsage, EmojiUsage.LIGHT)
        assert result == EmojiUsage.LIGHT

        result = parse_enum("", EmojiUsage, EmojiUsage.MODERATE)
        assert result == EmojiUsage.MODERATE

    def test_with_whitespace(self) -> None:
        assert parse_enum("  heavy  ", EmojiUsage, EmojiUsage.LIGHT) == EmojiUsage.HEAVY
        assert parse_enum("\theavy\n", EmojiUsage, EmojiUsage.LIGHT) == EmojiUsage.HEAVY

    def test_communication_frequency(self) -> None:
        assert (
            parse_enum("high", CommunicationFrequency, CommunicationFrequency.MEDIUM)
            == CommunicationFrequency.HIGH
        )
        assert (
            parse_enum("medium (texts daily)", CommunicationFrequency, CommunicationFrequency.LOW)
            == CommunicationFrequency.MEDIUM
        )

    def test_response_time(self) -> None:
        assert parse_enum("instant", ResponseTime, ResponseTime.MINUTES) == ResponseTime.INSTANT
        assert (
            parse_enum("minutes (usually responds quickly)", ResponseTime, ResponseTime.HOURS)
            == ResponseTime.MINUTES
        )

    def test_vocabulary_level(self) -> None:
        assert (
            parse_enum("sophisticated", VocabularyLevel, VocabularyLevel.MODERATE)
            == VocabularyLevel.SOPHISTICATED
        )
        assert (
            parse_enum("simple vocabulary", VocabularyLevel, VocabularyLevel.MODERATE)
            == VocabularyLevel.SIMPLE
        )
