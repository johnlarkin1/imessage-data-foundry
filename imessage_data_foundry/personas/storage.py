"""SQLite-based persona storage for foundry.db."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from imessage_data_foundry.personas.models import (
    CommunicationFrequency,
    EmojiUsage,
    IdentifierType,
    Persona,
    ResponseTime,
    VocabularyLevel,
)


class PersonaNotFoundError(Exception):
    """Raised when a persona is not found."""


FOUNDRY_SCHEMA = """
CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    identifier TEXT NOT NULL,
    identifier_type TEXT NOT NULL,
    country_code TEXT DEFAULT 'US',
    personality TEXT,
    writing_style TEXT,
    relationship TEXT,
    communication_frequency TEXT,
    typical_response_time TEXT,
    emoji_usage TEXT,
    vocabulary_level TEXT,
    topics_of_interest TEXT,
    is_self INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generation_history (
    id TEXT PRIMARY KEY,
    output_path TEXT NOT NULL,
    macos_version TEXT NOT NULL,
    persona_ids TEXT NOT NULL,
    message_count INTEGER,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_personas_name ON personas(name);
CREATE INDEX IF NOT EXISTS idx_personas_is_self ON personas(is_self);
CREATE INDEX IF NOT EXISTS idx_personas_identifier ON personas(identifier);
"""


def get_default_db_path() -> Path:
    """Get the default path for foundry.db."""
    config_path = os.environ.get("IMESSAGE_FOUNDRY_CONFIG")
    if config_path:
        return Path(config_path).parent / "foundry.db"

    xdg_path = Path.home() / ".config" / "imessage-data-foundry" / "foundry.db"
    if xdg_path.parent.exists() or not Path("./data").exists():
        return xdg_path

    return Path("./data/foundry.db")


class PersonaStorage:
    """SQLite-based storage for personas."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else get_default_db_path()
        self._connection: sqlite3.Connection | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._initialize()
        return self._connection  # type: ignore[return-value]

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.db_path))
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(FOUNDRY_SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> PersonaStorage:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def create(self, persona: Persona) -> Persona:
        """Create a new persona. Returns the created persona."""
        self.connection.execute(
            """
            INSERT INTO personas (
                id, name, identifier, identifier_type, country_code,
                personality, writing_style, relationship,
                communication_frequency, typical_response_time,
                emoji_usage, vocabulary_level, topics_of_interest,
                is_self, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._persona_to_row(persona),
        )
        self.connection.commit()
        return persona

    def get(self, persona_id: str) -> Persona:
        """Get a persona by ID. Raises PersonaNotFoundError if not found."""
        cursor = self.connection.execute("SELECT * FROM personas WHERE id = ?", (persona_id,))
        row = cursor.fetchone()
        if row is None:
            raise PersonaNotFoundError(f"Persona not found: {persona_id}")
        return self._row_to_persona(row)

    def get_by_name(self, name: str) -> list[Persona]:
        """Get personas by name (case-insensitive partial match)."""
        cursor = self.connection.execute(
            "SELECT * FROM personas WHERE name LIKE ? ORDER BY name",
            (f"%{name}%",),
        )
        return [self._row_to_persona(row) for row in cursor.fetchall()]

    def get_self(self) -> Persona | None:
        """Get the persona marked as self, if any."""
        cursor = self.connection.execute("SELECT * FROM personas WHERE is_self = 1 LIMIT 1")
        row = cursor.fetchone()
        return self._row_to_persona(row) if row else None

    def update(self, persona: Persona) -> Persona:
        """Update an existing persona. Raises PersonaNotFoundError if not found."""
        persona.updated_at = datetime.now(UTC)
        cursor = self.connection.execute(
            """
            UPDATE personas SET
                name = ?, identifier = ?, identifier_type = ?, country_code = ?,
                personality = ?, writing_style = ?, relationship = ?,
                communication_frequency = ?, typical_response_time = ?,
                emoji_usage = ?, vocabulary_level = ?, topics_of_interest = ?,
                is_self = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                persona.name,
                persona.identifier,
                persona.identifier_type.value,
                persona.country_code,
                persona.personality,
                persona.writing_style,
                persona.relationship,
                persona.communication_frequency.value,
                persona.typical_response_time.value,
                persona.emoji_usage.value,
                persona.vocabulary_level.value,
                json.dumps(persona.topics_of_interest),
                1 if persona.is_self else 0,
                persona.updated_at.isoformat(),
                persona.id,
            ),
        )
        if cursor.rowcount == 0:
            raise PersonaNotFoundError(f"Persona not found: {persona.id}")
        self.connection.commit()
        return persona

    def delete(self, persona_id: str) -> None:
        """Delete a persona by ID. Raises PersonaNotFoundError if not found."""
        cursor = self.connection.execute("DELETE FROM personas WHERE id = ?", (persona_id,))
        if cursor.rowcount == 0:
            raise PersonaNotFoundError(f"Persona not found: {persona_id}")
        self.connection.commit()

    def list_all(self) -> list[Persona]:
        """List all personas, ordered by name."""
        cursor = self.connection.execute("SELECT * FROM personas ORDER BY name")
        return [self._row_to_persona(row) for row in cursor.fetchall()]

    def count(self) -> int:
        """Return the total number of personas."""
        cursor = self.connection.execute("SELECT COUNT(*) FROM personas")
        return cursor.fetchone()[0]

    def exists(self, persona_id: str) -> bool:
        """Check if a persona exists."""
        cursor = self.connection.execute("SELECT 1 FROM personas WHERE id = ?", (persona_id,))
        return cursor.fetchone() is not None

    def create_many(self, personas: list[Persona]) -> list[Persona]:
        """Create multiple personas in a single transaction."""
        rows = [self._persona_to_row(p) for p in personas]
        self.connection.executemany(
            """
            INSERT INTO personas (
                id, name, identifier, identifier_type, country_code,
                personality, writing_style, relationship,
                communication_frequency, typical_response_time,
                emoji_usage, vocabulary_level, topics_of_interest,
                is_self, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.connection.commit()
        return personas

    def delete_all(self) -> int:
        """Delete all personas. Returns count of deleted rows."""
        cursor = self.connection.execute("DELETE FROM personas")
        self.connection.commit()
        return cursor.rowcount

    def export_all(self) -> list[dict[str, Any]]:
        """Export all personas as JSON-serializable dicts."""
        return [p.model_dump(mode="json") for p in self.list_all()]

    def import_personas(self, data: list[dict[str, Any]], replace: bool = False) -> list[Persona]:
        """Import personas from JSON data."""
        personas = [Persona.model_validate(d) for d in data]

        if replace:
            for persona in personas:
                if self.exists(persona.id):
                    self.update(persona)
                else:
                    self.create(persona)
        else:
            new_personas = [p for p in personas if not self.exists(p.id)]
            if new_personas:
                self.create_many(new_personas)
            personas = new_personas

        return personas

    def _persona_to_row(self, persona: Persona) -> tuple[Any, ...]:
        return (
            persona.id,
            persona.name,
            persona.identifier,
            persona.identifier_type.value,
            persona.country_code,
            persona.personality,
            persona.writing_style,
            persona.relationship,
            persona.communication_frequency.value,
            persona.typical_response_time.value,
            persona.emoji_usage.value,
            persona.vocabulary_level.value,
            json.dumps(persona.topics_of_interest),
            1 if persona.is_self else 0,
            persona.created_at.isoformat(),
            persona.updated_at.isoformat(),
        )

    def _row_to_persona(self, row: sqlite3.Row) -> Persona:
        topics = json.loads(row["topics_of_interest"]) if row["topics_of_interest"] else []
        return Persona(
            id=row["id"],
            name=row["name"],
            identifier=row["identifier"],
            identifier_type=IdentifierType(row["identifier_type"]),
            country_code=row["country_code"],
            personality=row["personality"] or "",
            writing_style=row["writing_style"] or "casual",
            relationship=row["relationship"] or "friend",
            communication_frequency=CommunicationFrequency(row["communication_frequency"]),
            typical_response_time=ResponseTime(row["typical_response_time"]),
            emoji_usage=EmojiUsage(row["emoji_usage"]),
            vocabulary_level=VocabularyLevel(row["vocabulary_level"]),
            topics_of_interest=topics,
            is_self=bool(row["is_self"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
