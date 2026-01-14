"""Application state management for the TUI wizard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from imessage_data_foundry.db.schema.base import SchemaVersion
from imessage_data_foundry.llm.config import ProviderType
from imessage_data_foundry.personas.models import ServiceType

if TYPE_CHECKING:
    from imessage_data_foundry.conversations.generator import GenerationResult


@dataclass
class AppState:
    """Central state for the TUI wizard.

    This state is shared across all screens and holds the configuration
    that accumulates as the user progresses through the wizard.
    """

    # Configuration
    macos_version: SchemaVersion = SchemaVersion.SEQUOIA
    output_path: Path = field(default_factory=lambda: Path("./output/chat.db"))
    provider_type: ProviderType | None = None

    # Persona selection (persona IDs)
    selected_persona_ids: list[str] = field(default_factory=list)

    # Conversation configuration
    message_count: int = 100
    time_range_start: datetime = field(
        default_factory=lambda: datetime.now(UTC) - timedelta(days=30)
    )
    time_range_end: datetime = field(default_factory=lambda: datetime.now(UTC))
    seed: str | None = None
    service: ServiceType = ServiceType.IMESSAGE

    # Generation results
    generation_result: GenerationResult | None = None

    def reset_generation(self) -> None:
        """Reset generation-related state for a new run."""
        self.generation_result = None

    def reset_all(self) -> None:
        """Reset all state to defaults."""
        self.macos_version = SchemaVersion.SEQUOIA
        self.output_path = Path("./output/chat.db")
        self.provider_type = None
        self.selected_persona_ids = []
        self.message_count = 100
        self.time_range_start = datetime.now(UTC) - timedelta(days=30)
        self.time_range_end = datetime.now(UTC)
        self.seed = None
        self.service = ServiceType.IMESSAGE
        self.generation_result = None


# Screen identifiers for navigation
class Screen:
    WELCOME = "welcome"
    CONFIG = "config"
    PERSONAS = "personas"
    CONVERSATIONS = "conversations"
    GENERATION = "generation"


# Wizard step metadata
WIZARD_STEPS = [
    (Screen.WELCOME, "Welcome", 1),
    (Screen.CONFIG, "Configuration", 2),
    (Screen.PERSONAS, "Personas", 3),
    (Screen.CONVERSATIONS, "Conversation", 4),
    (Screen.GENERATION, "Generate", 5),
]


def get_step_info(screen_id: str) -> tuple[int, int, str]:
    """Get (current_step, total_steps, title) for a screen."""
    for screen, title, step in WIZARD_STEPS:
        if screen == screen_id:
            return step, len(WIZARD_STEPS), title
    return 0, len(WIZARD_STEPS), "Unknown"
