import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

from imessage_data_foundry.personas import sql
from imessage_data_foundry.personas.models import (
    CommunicationFrequency,
    EmojiUsage,
    IdentifierType,
    Persona,
    ResponseTime,
    VocabularyLevel,
)
from imessage_data_foundry.utils.paths import get_default_db_path


class PersonaNotFoundError(Exception):
    """Raised when a persona is not found."""


class PersonaStorage:
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
        self._connection.executescript(sql.SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def create(self, persona: Persona) -> Persona:
        return self.create_many([persona])[0]

    def get(self, persona_id: str) -> Persona:
        """Raises PersonaNotFoundError if not found."""
        cursor = self.connection.execute(sql.SELECT_BY_ID, (persona_id,))
        row = cursor.fetchone()
        if row is None:
            raise PersonaNotFoundError(f"Persona not found: {persona_id}")
        return self._row_to_persona(row)

    def get_by_name(self, name: str) -> list[Persona]:
        """Get personas by name (case-insensitive partial match)."""
        cursor = self.connection.execute(sql.SELECT_BY_NAME, (f"%{name}%",))
        return [self._row_to_persona(row) for row in cursor.fetchall()]

    def get_self(self) -> Persona | None:
        """Get the persona marked as self, if any."""
        cursor = self.connection.execute(sql.SELECT_SELF)
        row = cursor.fetchone()
        return self._row_to_persona(row) if row else None

    def update(self, persona: Persona) -> Persona:
        """Update an existing persona. Raises PersonaNotFoundError if not found."""
        persona.updated_at = datetime.now(UTC)
        cursor = self.connection.execute(
            sql.UPDATE_PERSONA,
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
        """Raises PersonaNotFoundError if not found."""
        cursor = self.connection.execute(sql.DELETE_BY_ID, (persona_id,))
        if cursor.rowcount == 0:
            raise PersonaNotFoundError(f"Persona not found: {persona_id}")
        self.connection.commit()

    def list_all(self) -> list[Persona]:
        cursor = self.connection.execute(sql.SELECT_ALL)
        return [self._row_to_persona(row) for row in cursor.fetchall()]

    def count(self) -> int:
        cursor = self.connection.execute(sql.SELECT_COUNT)
        return cursor.fetchone()[0]

    def exists(self, persona_id: str) -> bool:
        cursor = self.connection.execute(sql.SELECT_EXISTS, (persona_id,))
        return cursor.fetchone() is not None

    def create_many(self, personas: list[Persona]) -> list[Persona]:
        rows = [self._persona_to_row(p) for p in personas]
        self.connection.executemany(sql.INSERT_PERSONA, rows)
        self.connection.commit()
        return personas

    def delete_all(self) -> int:
        """Delete all personas. Returns count of deleted rows."""
        cursor = self.connection.execute(sql.DELETE_ALL)
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
            writing_style=row["writing_style"] or "",
            relationship=row["relationship"] or "",
            communication_frequency=CommunicationFrequency(row["communication_frequency"]),
            typical_response_time=ResponseTime(row["typical_response_time"]),
            emoji_usage=EmojiUsage(row["emoji_usage"]),
            vocabulary_level=VocabularyLevel(row["vocabulary_level"]),
            topics_of_interest=topics,
            is_self=bool(row["is_self"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
