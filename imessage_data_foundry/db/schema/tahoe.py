from imessage_data_foundry.db.schema import sequoia

SCHEMA_VERSION: str = "tahoe"
MACOS_VERSIONS: list[str] = ["26.0"]
CLIENT_VERSION: str = "26001"

MESSAGE_TABLE: str = sequoia.MESSAGE_TABLE
ATTACHMENT_TABLE: str = sequoia.ATTACHMENT_TABLE


def get_tables() -> dict[str, str]:
    return sequoia.get_tables()


def get_indexes() -> list[str]:
    return sequoia.get_indexes()


def get_triggers() -> list[str]:
    return sequoia.get_triggers()


def get_metadata() -> dict[str, str]:
    metadata = sequoia.get_metadata().copy()
    metadata["_ClientVersion"] = CLIENT_VERSION
    return metadata
