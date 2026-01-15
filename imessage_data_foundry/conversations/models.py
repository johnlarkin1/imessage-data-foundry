from typing import Self
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from imessage_data_foundry.personas.models import IdentifierType, Persona


class Message(BaseModel):
    """A single message in a conversation."""

    guid: str = Field(default_factory=lambda: f"p:0/{uuid4()}")
    text: str | None = None

    handle_id: int | None = Field(default=None)
    is_from_me: bool = False

    date: int = Field(..., description="Apple epoch nanoseconds")
    date_read: int | None = None
    date_delivered: int | None = None

    service: str = "iMessage"

    is_delivered: bool = True
    is_sent: bool = True
    is_read: bool = True
    is_finished: bool = True

    cache_roomnames: str | None = None
    chat_id: int | None = Field(default=None, exclude=True)

    @field_validator("guid")
    @classmethod
    def validate_guid(cls, v: str) -> str:
        if not v or len(v) < 10:
            return f"p:0/{uuid4()}"
        return v

    @classmethod
    def create_outgoing(
        cls,
        text: str,
        date: int,
        service: str = "iMessage",
    ) -> Self:
        return cls(
            text=text,
            date=date,
            is_from_me=True,
            handle_id=None,
            service=service,
            is_sent=True,
            is_delivered=True,
        )

    @classmethod
    def create_incoming(
        cls,
        text: str,
        date: int,
        handle_id: int,
        service: str = "iMessage",
    ) -> Self:
        return cls(
            text=text,
            date=date,
            is_from_me=False,
            handle_id=handle_id,
            service=service,
            is_read=True,
            is_delivered=True,
        )


class Chat(BaseModel):
    """A conversation thread (direct or group)."""

    guid: str = Field(...)
    style: int = Field(default=43)
    state: int = Field(default=3)
    chat_identifier: str = Field(...)
    service_name: str = "iMessage"
    display_name: str | None = None

    handle_ids: list[int] = Field(default_factory=list, exclude=True)

    @classmethod
    def create_direct(
        cls,
        identifier: str,
        service: str = "iMessage",
    ) -> Self:
        service_prefix = service if service in ("iMessage", "SMS") else "iMessage"
        return cls(
            guid=f"{service_prefix};-;{identifier}",
            style=43,
            chat_identifier=identifier,
            service_name=service_prefix,
        )

    @classmethod
    def create_group(
        cls,
        display_name: str | None = None,
        service: str = "iMessage",
    ) -> Self:
        service_prefix = service if service in ("iMessage", "SMS") else "iMessage"
        group_id = f"chat{uuid4().hex[:12]}"
        return cls(
            guid=f"{service_prefix};+;{group_id}",
            style=45,
            chat_identifier=group_id,
            service_name=service_prefix,
            display_name=display_name,
        )


class Handle(BaseModel):
    """A contact identifier (phone or email)."""

    id: str = Field(...)
    country: str | None = "US"
    service: str = "iMessage"
    uncanonicalized_id: str | None = None
    person_centric_id: str | None = None

    @classmethod
    def from_persona(cls, persona: Persona) -> Self:
        return cls(
            id=persona.identifier,
            country=persona.country_code
            if persona.identifier_type == IdentifierType.PHONE
            else None,
            service="iMessage",
        )


class Attachment(BaseModel):
    """Metadata for a file attachment."""

    guid: str = Field(default_factory=lambda: f"at_0_{uuid4()}")
    filename: str | None = None
    uti: str | None = None
    mime_type: str | None = None
    total_bytes: int = 0
    is_outgoing: bool = False
    created_date: int | None = None
    transfer_state: int = 5
