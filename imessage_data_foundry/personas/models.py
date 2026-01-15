from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationInfo, computed_field, field_validator

from imessage_data_foundry.utils.phone_numbers import format_national


class IdentifierType(str, Enum):
    PHONE = "phone"
    EMAIL = "email"


class CommunicationFrequency(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResponseTime(str, Enum):
    INSTANT = "instant"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"


class EmojiUsage(str, Enum):
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"


class VocabularyLevel(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    SOPHISTICATED = "sophisticated"


class ChatType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"


class ServiceType(str, Enum):
    IMESSAGE = "iMessage"
    SMS = "SMS"


class Persona(BaseModel):
    """A persona representing a contact in generated conversations."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    identifier: str = Field(..., description="Phone number (E.164) or email")
    identifier_type: IdentifierType = IdentifierType.PHONE
    country_code: str = Field(default="US", pattern=r"^[A-Z]{2}$")

    personality: str = Field(default="", max_length=500)
    writing_style: str = Field(default="casual", max_length=200)
    relationship: str = Field(default="friend", max_length=100)

    communication_frequency: CommunicationFrequency = CommunicationFrequency.MEDIUM
    typical_response_time: ResponseTime = ResponseTime.MINUTES
    emoji_usage: EmojiUsage = EmojiUsage.LIGHT
    vocabulary_level: VocabularyLevel = VocabularyLevel.MODERATE
    topics_of_interest: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_self: bool = Field(default=False)

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("identifier cannot be empty")
        return v

    @field_validator("topics_of_interest")
    @classmethod
    def validate_topics(cls, v: list[str]) -> list[str]:
        return [topic.strip() for topic in v if topic.strip()]

    @computed_field  # type: ignore[misc]
    @property
    def display_identifier(self) -> str:
        if self.identifier_type == IdentifierType.EMAIL:
            return self.identifier
        try:
            return format_national(self.identifier, self.country_code)
        except Exception:
            return self.identifier


class ConversationConfig(BaseModel):
    """Configuration for generating a conversation."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str | None = Field(default=None, max_length=100)
    participants: list[str] = Field(..., min_length=2)
    chat_type: ChatType = ChatType.DIRECT

    message_count_target: int = Field(default=100, ge=1, le=10000)
    time_range_start: datetime
    time_range_end: datetime
    seed: str | None = Field(default=None, max_length=500)

    service: ServiceType = ServiceType.IMESSAGE

    @field_validator("participants")
    @classmethod
    def validate_participants(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("At least 2 participants required")
        if len(set(v)) != len(v):
            raise ValueError("Duplicate participants not allowed")
        return v

    @field_validator("time_range_end")
    @classmethod
    def validate_time_range(cls, v: datetime, info: ValidationInfo) -> datetime:
        start = info.data.get("time_range_start") if info.data else None
        if start and v <= start:
            raise ValueError("time_range_end must be after time_range_start")
        return v

    @field_validator("chat_type")
    @classmethod
    def validate_chat_type(cls, v: ChatType, info: ValidationInfo) -> ChatType:
        participants = info.data.get("participants", []) if info.data else []
        if v == ChatType.DIRECT and len(participants) > 2:
            raise ValueError("Direct chat can only have 2 participants")
        return v
