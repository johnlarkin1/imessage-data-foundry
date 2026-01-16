from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

from InquirerPy import inquirer
from InquirerPy.validator import EmptyInputValidator, NumberValidator

from imessage_data_foundry.personas.models import (
    CommunicationFrequency,
    EmojiUsage,
    Persona,
    ResponseTime,
    VocabularyLevel,
)

E = TypeVar("E", bound=Enum)

MAIN_MENU_CHOICES = [
    {"name": "Quick Start - Auto-generate personas and conversations", "value": "quick_start"},
    {"name": "Guided - Create personas manually with full control", "value": "guided"},
    {"name": "Manage Personas - Edit or delete existing personas", "value": "manage"},
    {"name": "Exit", "value": "exit"},
]


def main_menu_prompt() -> str:
    result = inquirer.select(
        message="What would you like to do?",
        choices=MAIN_MENU_CHOICES,
    ).execute()
    return result if result else "exit"


def confirm_prompt(message: str, default: bool = True) -> bool:
    result = inquirer.confirm(message=message, default=default).execute()
    return result if result is not None else False


def text_prompt(message: str, default: str = "", validate: bool = False) -> str:
    prompt = inquirer.text(
        message=message,
        default=default,
        validate=EmptyInputValidator("This field cannot be empty") if validate else None,
    )
    result = prompt.execute()
    return result.strip() if result else default


def int_prompt(message: str, default: int, min_val: int = 1, max_val: int = 10000) -> int:
    result = inquirer.number(
        message=message,
        default=default,
        min_allowed=min_val,
        max_allowed=max_val,
        validate=NumberValidator(),
    ).execute()
    return int(result) if result is not None else default


def enum_prompt(message: str, enum_class: type[E], default: E | None = None) -> E:
    choices = [
        {"name": member.value.replace("_", " ").title(), "value": member} for member in enum_class
    ]
    default_choice = default if default else list(enum_class)[0]

    result = inquirer.select(
        message=message,
        choices=choices,
        default=default_choice,
    ).execute()
    return result if result else default_choice


def topics_prompt(message: str = "Topics of interest (comma-separated)") -> list[str]:
    result = inquirer.text(message=message, default="").execute()
    if not result or not result.strip():
        return []
    return [t.strip() for t in result.split(",") if t.strip()]


def persona_input_prompts(is_self: bool = False, existing: Persona | None = None) -> dict[str, Any]:
    default_name = existing.name if existing else ""
    default_personality = existing.personality if existing else ""
    default_writing_style = existing.writing_style if existing else "casual"
    default_relationship = existing.relationship if existing else ("self" if is_self else "friend")
    default_comm_freq = (
        existing.communication_frequency if existing else CommunicationFrequency.MEDIUM
    )
    default_response_time = existing.typical_response_time if existing else ResponseTime.MINUTES
    default_emoji = existing.emoji_usage if existing else EmojiUsage.LIGHT
    default_vocab = existing.vocabulary_level if existing else VocabularyLevel.MODERATE
    default_topics = existing.topics_of_interest if existing else []

    label = "your" if is_self else "this persona's"

    result: dict[str, Any] = {}
    result["name"] = text_prompt(f"Enter {label} name", default=default_name, validate=True)
    result["personality"] = text_prompt(
        f"Describe {label} personality (2-3 sentences)",
        default=default_personality,
    )
    result["writing_style"] = text_prompt(
        f"Describe {label} writing style (e.g., casual, formal, uses slang)",
        default=default_writing_style,
    )

    if not is_self:
        result["relationship"] = text_prompt(
            "Relationship to you (e.g., friend, coworker, family)",
            default=default_relationship,
        )
    else:
        result["relationship"] = "self"

    result["communication_frequency"] = enum_prompt(
        "Communication frequency",
        CommunicationFrequency,
        default=default_comm_freq,
    )
    result["typical_response_time"] = enum_prompt(
        "Typical response time",
        ResponseTime,
        default=default_response_time,
    )
    result["emoji_usage"] = enum_prompt(
        "Emoji usage",
        EmojiUsage,
        default=default_emoji,
    )
    result["vocabulary_level"] = enum_prompt(
        "Vocabulary level",
        VocabularyLevel,
        default=default_vocab,
    )

    topics_default_str = ", ".join(default_topics) if default_topics else ""
    topics_input = text_prompt("Topics of interest (comma-separated)", default=topics_default_str)
    result["topics_of_interest"] = [t.strip() for t in topics_input.split(",") if t.strip()]

    return result


def select_personas_prompt(
    personas: list[Persona], message: str = "Select personas"
) -> list[Persona]:
    if not personas:
        return []

    choices = [{"name": f"{p.name} ({p.display_identifier})", "value": p} for p in personas]
    result = inquirer.checkbox(message=message, choices=choices).execute()
    return result if result else []


def select_single_persona_prompt(
    personas: list[Persona],
    message: str = "Select a persona",
    include_back: bool = True,
) -> Persona | None:
    if not personas:
        return None

    choices: list[dict[str, Any]] = [
        {"name": f"{p.name} ({p.display_identifier})", "value": p} for p in personas
    ]
    if include_back:
        choices.append({"name": "< Back", "value": None})

    result = inquirer.select(message=message, choices=choices).execute()
    return result


def conversation_seed_prompt() -> str | None:
    result = inquirer.text(
        message="Conversation topic/seed (optional, press Enter to skip)",
        default="",
    ).execute()
    seed = result.strip() if result else ""
    return seed if seed else None


def simulation_type_prompt() -> str:
    choices = [
        {"name": "Automated - Generate all pairwise conversations", "value": "automated"},
        {"name": "Curated - Pick specific pairs and topics", "value": "curated"},
    ]
    result = inquirer.select(
        message="How would you like to generate conversations?",
        choices=choices,
    ).execute()
    return result if result else "automated"


def manage_action_prompt() -> str:
    choices = [
        {"name": "Edit a persona", "value": "edit"},
        {"name": "Delete a persona", "value": "delete"},
        {"name": "< Back to main menu", "value": "back"},
    ]
    result = inquirer.select(
        message="What would you like to do?",
        choices=choices,
    ).execute()
    return result if result else "back"


def database_exists_prompt(path: Path) -> tuple[str, Path | None]:
    choices = [
        {"name": "Overwrite existing database", "value": "overwrite"},
        {"name": "Append to existing database", "value": "append"},
        {"name": "Use a different path", "value": "new_path"},
        {"name": "Cancel", "value": "cancel"},
    ]
    action = inquirer.select(
        message=f"Database already exists at {path}. What would you like to do?",
        choices=choices,
    ).execute()

    new_path = None
    if action == "new_path":
        new_path_str = inquirer.text(
            message="Enter new database path:",
            default=str(path.parent / "chat_new.db"),
        ).execute()
        new_path = Path(new_path_str) if new_path_str else None

    return action if action else "cancel", new_path
