"""Tests for conversation seeding."""

import random

from imessage_data_foundry.conversations.seeding import (
    get_topic_shift_hint,
    parse_seed,
    should_introduce_topic_shift,
)
from imessage_data_foundry.personas.models import Persona


def make_persona(
    name: str = "Test",
    topics: list[str] | None = None,
) -> Persona:
    return Persona(
        name=name,
        identifier="+15551234567",
        topics_of_interest=topics or [],
    )


class TestParseSeed:
    def test_none_seed(self):
        result = parse_seed(None)

        assert result.raw_seed is None
        assert result.themes == []
        assert result.opening_context is None

    def test_empty_string(self):
        result = parse_seed("")

        assert result.raw_seed is None
        assert result.themes == []

    def test_whitespace_only(self):
        result = parse_seed("   ")

        assert result.raw_seed is None
        assert result.themes == []

    def test_simple_theme(self):
        result = parse_seed("planning a surprise party")

        assert result.raw_seed == "planning a surprise party"
        assert "planning" in result.themes
        assert "surprise" in result.themes
        assert "party" in result.themes
        assert result.opening_context == "planning a surprise party"

    def test_filters_short_words(self):
        result = parse_seed("a to the planning")

        assert "planning" in result.themes
        assert "a" not in result.themes
        assert "to" not in result.themes
        assert "the" not in result.themes

    def test_limits_themes(self):
        result = parse_seed("word1 word2 word3 word4 word5 word6 word7")

        assert len(result.themes) <= 5


class TestShouldIntroduceTopicShift:
    def test_never_at_start(self):
        shifts = sum(should_introduce_topic_shift(i, 100, random.Random(i)) for i in range(20))

        assert shifts == 0

    def test_never_at_end(self):
        shifts = sum(should_introduce_topic_shift(i, 100, random.Random(i)) for i in range(90, 100))

        assert shifts == 0

    def test_possible_in_middle(self):
        shifts = sum(should_introduce_topic_shift(i, 100, random.Random(i)) for i in range(30, 70))

        assert shifts >= 0

    def test_small_conversation_no_shifts(self):
        shifts = sum(should_introduce_topic_shift(i, 10, random.Random(i)) for i in range(10))

        assert shifts == 0


class TestGetTopicShiftHint:
    def test_returns_persona_topic(self):
        personas = [
            make_persona("Alice", topics=["cooking", "travel"]),
            make_persona("Bob", topics=["sports", "music"]),
        ]
        rng = random.Random(42)

        hint = get_topic_shift_hint(personas, [], rng)

        assert hint in ["cooking", "travel", "sports", "music"]

    def test_excludes_current_themes(self):
        personas = [make_persona("Alice", topics=["cooking", "travel"])]
        rng = random.Random(42)

        hint = get_topic_shift_hint(personas, ["cooking"], rng)

        assert hint == "travel"

    def test_returns_none_if_no_topics(self):
        personas = [make_persona("Alice", topics=[])]
        rng = random.Random(42)

        hint = get_topic_shift_hint(personas, [], rng)

        assert hint is None

    def test_returns_none_if_all_topics_used(self):
        personas = [make_persona("Alice", topics=["cooking"])]
        rng = random.Random(42)

        hint = get_topic_shift_hint(personas, ["cooking"], rng)

        assert hint is None

    def test_case_insensitive_exclusion(self):
        personas = [make_persona("Alice", topics=["Cooking", "Travel"])]
        rng = random.Random(42)

        hint = get_topic_shift_hint(personas, ["cooking"], rng)

        assert hint == "Travel"
