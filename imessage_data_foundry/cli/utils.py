from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path

from imessage_data_foundry.cli.components.prompts import (
    database_exists_prompt,
    existing_self_prompt,
)
from imessage_data_foundry.llm.models import GeneratedPersona
from imessage_data_foundry.personas.models import IdentifierType, Persona
from imessage_data_foundry.utils.phone_numbers import generate_fake_phone


class DatabaseExistsAction(str, Enum):
    OVERWRITE = "overwrite"
    APPEND = "append"
    CANCEL = "cancel"
    NEW_PATH = "new_path"


DEFAULT_PERSONA_COUNT = 4
DEFAULT_MESSAGE_COUNT = 100
DEFAULT_OUTPUT_PATH = Path("./output/chat.db")
DEFAULT_ADDRESSBOOK_NAME = "addressbook.db"
DEFAULT_TIME_RANGE_DAYS = 30


def get_addressbook_path(chat_db_path: Path) -> Path:
    return chat_db_path.parent / DEFAULT_ADDRESSBOOK_NAME


def ensure_output_dir(output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def get_default_time_range() -> tuple[datetime, datetime]:
    end = datetime.now(UTC)
    start = end - timedelta(days=DEFAULT_TIME_RANGE_DAYS)
    return start, end


def generated_to_full_persona(
    gen: GeneratedPersona,
    is_self: bool = False,
    identifier: str | None = None,
    country_code: str = "US",
) -> Persona:
    return Persona(
        name=gen.name,
        identifier=identifier or generate_fake_phone(country_code),
        identifier_type=IdentifierType.PHONE,
        country_code=country_code,
        personality=gen.personality,
        writing_style=gen.writing_style,
        relationship=gen.relationship if not is_self else "self",
        communication_frequency=gen.communication_frequency,
        typical_response_time=gen.typical_response_time,
        emoji_usage=gen.emoji_usage,
        vocabulary_level=gen.vocabulary_level,
        topics_of_interest=gen.topics_of_interest,
        is_self=is_self,
    )


def create_self_persona(
    name: str,
    personality: str = "",
    writing_style: str = "casual",
    identifier: str | None = None,
    country_code: str = "US",
) -> Persona:
    return Persona(
        name=name,
        identifier=identifier or generate_fake_phone(country_code),
        identifier_type=IdentifierType.PHONE,
        country_code=country_code,
        personality=personality,
        writing_style=writing_style,
        relationship="self",
        is_self=True,
    )


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining = seconds % 60
    return f"{minutes}m {remaining:.0f}s"


def handle_existing_database(output_path: Path) -> tuple[DatabaseExistsAction, Path]:
    if not output_path.exists():
        return DatabaseExistsAction.OVERWRITE, output_path

    action_str, new_path = database_exists_prompt(output_path)
    action = DatabaseExistsAction(action_str)
    final_path = new_path or output_path

    if action == DatabaseExistsAction.OVERWRITE:
        output_path.unlink()

    return action, final_path


def prompt_use_existing_self(existing_self: Persona) -> bool:
    return existing_self_prompt(existing_self)
