from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from imessage_data_foundry.personas.models import (
    ChatType,
    CommunicationFrequency,
    ConversationConfig,
    EmojiUsage,
    IdentifierType,
    Persona,
    ResponseTime,
    ServiceType,
    VocabularyLevel,
)


class TestPersonaCreation:
    def test_minimal_persona(self):
        persona = Persona(name="Test User", identifier="+15551234567")
        assert persona.name == "Test User"
        assert persona.identifier == "+15551234567"
        assert persona.id is not None
        assert len(persona.id) == 36  # UUID length

    def test_all_fields(self):
        persona = Persona(
            name="Alex Chen",
            identifier="+15551234567",
            identifier_type=IdentifierType.PHONE,
            country_code="US",
            personality="Friendly and outgoing",
            writing_style="casual",
            relationship="close friend",
            communication_frequency=CommunicationFrequency.HIGH,
            typical_response_time=ResponseTime.MINUTES,
            emoji_usage=EmojiUsage.MODERATE,
            vocabulary_level=VocabularyLevel.MODERATE,
            topics_of_interest=["movies", "hiking"],
            is_self=False,
        )
        assert persona.communication_frequency == CommunicationFrequency.HIGH
        assert persona.topics_of_interest == ["movies", "hiking"]

    def test_email_identifier(self):
        persona = Persona(
            name="Email User",
            identifier="user@example.com",
            identifier_type=IdentifierType.EMAIL,
        )
        assert persona.identifier_type == IdentifierType.EMAIL
        assert persona.identifier == "user@example.com"

    def test_auto_generated_id_unique(self):
        p1 = Persona(name="Test1", identifier="+15551234567")
        p2 = Persona(name="Test2", identifier="+15559876543")
        assert p1.id != p2.id


class TestPersonaValidation:
    def test_empty_name_fails(self):
        with pytest.raises(ValidationError):
            Persona(name="", identifier="+15551234567")

    def test_empty_identifier_fails(self):
        with pytest.raises(ValidationError):
            Persona(name="Test", identifier="")

    def test_whitespace_identifier_fails(self):
        with pytest.raises(ValidationError):
            Persona(name="Test", identifier="   ")

    def test_invalid_country_code_fails(self):
        with pytest.raises(ValidationError):
            Persona(name="Test", identifier="+15551234567", country_code="USA")

    def test_lowercase_country_code_fails(self):
        with pytest.raises(ValidationError):
            Persona(name="Test", identifier="+15551234567", country_code="us")

    def test_name_too_long_fails(self):
        with pytest.raises(ValidationError):
            Persona(name="x" * 101, identifier="+15551234567")


class TestPersonaDefaults:
    def test_default_values(self):
        persona = Persona(name="Test", identifier="+15551234567")
        assert persona.identifier_type == IdentifierType.PHONE
        assert persona.country_code == "US"
        assert persona.communication_frequency == CommunicationFrequency.MEDIUM
        assert persona.typical_response_time == ResponseTime.MINUTES
        assert persona.emoji_usage == EmojiUsage.LIGHT
        assert persona.vocabulary_level == VocabularyLevel.MODERATE
        assert persona.is_self is False
        assert persona.topics_of_interest == []
        assert persona.personality == ""
        assert persona.writing_style == "casual"
        assert persona.relationship == "friend"

    def test_created_at_is_set(self):
        persona = Persona(name="Test", identifier="+15551234567")
        assert persona.created_at is not None
        assert persona.updated_at is not None


class TestPersonaTopicsValidation:
    def test_empty_topics_stripped(self):
        persona = Persona(
            name="Test",
            identifier="+15551234567",
            topics_of_interest=["movies", "", "  ", "hiking"],
        )
        assert persona.topics_of_interest == ["movies", "hiking"]


class TestConversationConfigCreation:
    def test_minimal_config(self):
        config = ConversationConfig(
            participants=["uuid-1", "uuid-2"],
            time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
            time_range_end=datetime(2024, 6, 1, tzinfo=UTC),
        )
        assert len(config.participants) == 2
        assert config.chat_type == ChatType.DIRECT

    def test_group_config(self):
        config = ConversationConfig(
            name="Friends Group",
            participants=["uuid-1", "uuid-2", "uuid-3"],
            chat_type=ChatType.GROUP,
            time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
            time_range_end=datetime(2024, 6, 1, tzinfo=UTC),
        )
        assert config.chat_type == ChatType.GROUP
        assert config.name == "Friends Group"

    def test_with_seed(self):
        config = ConversationConfig(
            participants=["uuid-1", "uuid-2"],
            time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
            time_range_end=datetime(2024, 6, 1, tzinfo=UTC),
            seed="planning a birthday party",
        )
        assert config.seed == "planning a birthday party"


class TestConversationConfigValidation:
    def test_single_participant_fails(self):
        with pytest.raises(ValidationError):
            ConversationConfig(
                participants=["uuid-1"],
                time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
                time_range_end=datetime(2024, 6, 1, tzinfo=UTC),
            )

    def test_duplicate_participants_fails(self):
        with pytest.raises(ValidationError):
            ConversationConfig(
                participants=["uuid-1", "uuid-1"],
                time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
                time_range_end=datetime(2024, 6, 1, tzinfo=UTC),
            )

    def test_invalid_time_range_fails(self):
        with pytest.raises(ValidationError):
            ConversationConfig(
                participants=["uuid-1", "uuid-2"],
                time_range_start=datetime(2024, 6, 1, tzinfo=UTC),
                time_range_end=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_direct_chat_with_three_participants_fails(self):
        with pytest.raises(ValidationError):
            ConversationConfig(
                participants=["uuid-1", "uuid-2", "uuid-3"],
                chat_type=ChatType.DIRECT,
                time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
                time_range_end=datetime(2024, 6, 1, tzinfo=UTC),
            )

    def test_message_count_bounds(self):
        with pytest.raises(ValidationError):
            ConversationConfig(
                participants=["uuid-1", "uuid-2"],
                time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
                time_range_end=datetime(2024, 6, 1, tzinfo=UTC),
                message_count_target=0,
            )

        with pytest.raises(ValidationError):
            ConversationConfig(
                participants=["uuid-1", "uuid-2"],
                time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
                time_range_end=datetime(2024, 6, 1, tzinfo=UTC),
                message_count_target=10001,
            )


class TestConversationConfigDefaults:
    def test_default_values(self):
        config = ConversationConfig(
            participants=["uuid-1", "uuid-2"],
            time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
            time_range_end=datetime(2024, 6, 1, tzinfo=UTC),
        )
        assert config.message_count_target == 100
        assert config.service == ServiceType.IMESSAGE
        assert config.chat_type == ChatType.DIRECT
        assert config.name is None
        assert config.seed is None
