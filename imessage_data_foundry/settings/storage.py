import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

from imessage_data_foundry.llm.config import ProviderType
from imessage_data_foundry.utils.paths import get_default_db_path

SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

SELECT_SETTING = "SELECT value FROM settings WHERE key = ?"
UPSERT_SETTING = """
INSERT INTO settings (key, value, updated_at)
VALUES (?, ?, ?)
ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
"""

PROVIDER_KEY = "default_provider"


class SettingsStorage:
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
        self._connection.executescript(SETTINGS_SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def get_provider(self) -> ProviderType | None:
        cursor = self.connection.execute(SELECT_SETTING, (PROVIDER_KEY,))
        row = cursor.fetchone()
        if row is None:
            return None
        try:
            return ProviderType(row["value"])
        except ValueError:
            return None

    def set_provider(self, provider: ProviderType) -> None:
        self.connection.execute(
            UPSERT_SETTING,
            (PROVIDER_KEY, provider.value, datetime.now(UTC).isoformat()),
        )
        self.connection.commit()
