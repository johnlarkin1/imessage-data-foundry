"""macOS 26 Tahoe iMessage database schema.

EXPERIMENTAL: macOS 26 Tahoe has not been released yet.
This schema is based on Sequoia and will be updated when Tahoe is available.
"""

from imessage_data_foundry.db.schema import sequoia

SCHEMA_VERSION: str = "tahoe"
MACOS_VERSIONS: list[str] = ["26.0"]
CLIENT_VERSION: str = "26001"

# Tahoe uses Sequoia schema as baseline until actual schema is known
MESSAGE_TABLE: str = sequoia.MESSAGE_TABLE
ATTACHMENT_TABLE: str = sequoia.ATTACHMENT_TABLE


def get_tables() -> dict[str, str]:
    """Return all table CREATE statements for Tahoe.

    Currently identical to Sequoia. Will be updated when Tahoe is released.
    """
    return sequoia.get_tables()


def get_indexes() -> list[str]:
    """Return all index CREATE statements for Tahoe."""
    return sequoia.get_indexes()


def get_triggers() -> list[str]:
    """Return all trigger CREATE statements for Tahoe."""
    return sequoia.get_triggers()


def get_metadata() -> dict[str, str]:
    """Return _SqliteDatabaseProperties content for Tahoe."""
    metadata = sequoia.get_metadata().copy()
    metadata["_ClientVersion"] = CLIENT_VERSION
    return metadata
