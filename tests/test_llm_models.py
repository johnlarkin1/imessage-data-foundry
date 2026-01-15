import pytest
from pydantic import ValidationError

from imessage_data_foundry.llm.models import (
    GeneratedMessage,
    GeneratedPersona,
    PersonaConstraints,
)
from imessage_data_foundry.personas.models import (
    CommunicationFrequency,
    EmojiUsage,
    ResponseTime,
    VocabularyLevel,
)


class TestPersonaConstraints:
    def test_empty_constraints(self):
        constraints = PersonaConstraints()
        assert constraints.relationship is None
        assert constraints.communication_frequency is None
        assert constraints.vocabulary_level is None

    def test_with_relationship(self):
        constraints = PersonaConstraints(relationship="friend")
        assert constraints.relationship == "friend"

    def test_with_all_fields(self):
        constraints = PersonaConstraints(
            relationship="family",
            communication_frequency=CommunicationFrequency.HIGH,
            typical_response_time=ResponseTime.INSTANT,
            emoji_usage=EmojiUsage.HEAVY,
            vocabulary_level=VocabularyLevel.SIMPLE,
            age_range=(18, 25),
            topics=["sports", "gaming"],
            personality_traits=["outgoing", "funny"],
        )
        assert constraints.relationship == "family"
        assert constraints.communication_frequency == CommunicationFrequency.HIGH
        assert constraints.age_range == (18, 25)
        assert "sports" in constraints.topics

    def test_age_range_tuple(self):
        constraints = PersonaConstraints(age_range=(20, 30))
        assert constraints.age_range[0] == 20
        assert constraints.age_range[1] == 30


class TestGeneratedMessage:
    def test_basic_message(self):
        msg = GeneratedMessage(text="Hello!", sender_id="person-1", is_from_me=False)
        assert msg.text == "Hello!"
        assert msg.sender_id == "person-1"
        assert msg.is_from_me is False

    def test_from_me_message(self):
        msg = GeneratedMessage(text="Hi there", sender_id="self-id", is_from_me=True)
        assert msg.is_from_me is True

    def test_missing_text_raises(self):
        with pytest.raises(ValidationError):
            GeneratedMessage(sender_id="person-1", is_from_me=False)

    def test_missing_sender_id_raises(self):
        with pytest.raises(ValidationError):
            GeneratedMessage(text="Hello!", is_from_me=False)

    def test_empty_text_allowed(self):
        msg = GeneratedMessage(text="", sender_id="person-1", is_from_me=False)
        assert msg.text == ""


class TestGeneratedPersona:
    def test_minimal_persona(self):
        persona = GeneratedPersona(
            name="John Doe",
            personality="Friendly and outgoing",
            writing_style="casual",
            relationship="friend",
        )
        assert persona.name == "John Doe"
        assert persona.personality == "Friendly and outgoing"
        assert persona.communication_frequency == CommunicationFrequency.MEDIUM
        assert persona.emoji_usage == EmojiUsage.LIGHT

    def test_full_persona(self):
        persona = GeneratedPersona(
            name="Jane Smith",
            personality="Reserved but thoughtful",
            writing_style="formal",
            relationship="coworker",
            communication_frequency=CommunicationFrequency.LOW,
            typical_response_time=ResponseTime.HOURS,
            emoji_usage=EmojiUsage.NONE,
            vocabulary_level=VocabularyLevel.SOPHISTICATED,
            topics_of_interest=["tech", "books"],
        )
        assert persona.name == "Jane Smith"
        assert persona.communication_frequency == CommunicationFrequency.LOW
        assert persona.vocabulary_level == VocabularyLevel.SOPHISTICATED
        assert len(persona.topics_of_interest) == 2

    def test_missing_required_fields_raises(self):
        with pytest.raises(ValidationError):
            GeneratedPersona(name="John")

    def test_default_topics(self):
        persona = GeneratedPersona(
            name="Test",
            personality="Test",
            writing_style="casual",
            relationship="friend",
        )
        assert persona.topics_of_interest == []

    def test_from_dict(self):
        data = {
            "name": "From Dict",
            "personality": "Test personality",
            "writing_style": "casual",
            "relationship": "friend",
            "communication_frequency": "high",
            "typical_response_time": "instant",
            "emoji_usage": "heavy",
            "vocabulary_level": "simple",
            "topics_of_interest": ["memes", "gaming"],
        }
        persona = GeneratedPersona.model_validate(data)
        assert persona.name == "From Dict"
        assert persona.communication_frequency == CommunicationFrequency.HIGH

    def test_string_coercion_to_enum(self):
        """Verify LLM string responses still parse correctly."""
        data = {
            "name": "Test Coercion",
            "personality": "Test personality",
            "writing_style": "casual",
            "relationship": "friend",
            "communication_frequency": "high",
            "typical_response_time": "instant",
            "emoji_usage": "heavy",
            "vocabulary_level": "simple",
            "topics_of_interest": ["memes"],
        }
        persona = GeneratedPersona.model_validate(data)
        assert persona.communication_frequency == CommunicationFrequency.HIGH
        assert isinstance(persona.communication_frequency, CommunicationFrequency)
        assert persona.typical_response_time == ResponseTime.INSTANT
        assert isinstance(persona.typical_response_time, ResponseTime)
