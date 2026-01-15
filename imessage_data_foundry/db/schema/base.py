from enum import Enum
from uuid import uuid4


class SchemaVersion(str, Enum):
    SONOMA = "sonoma"
    SEQUOIA = "sequoia"
    TAHOE = "tahoe"


def generate_message_guid() -> str:
    return f"p:0/{uuid4()!s}"


def generate_chat_guid(service: str, chat_type: str, identifier: str) -> str:
    separator = "-" if chat_type == "direct" else "+"
    return f"{service};{separator};{identifier}"


def generate_attachment_guid() -> str:
    return f"at_0_{uuid4()!s}"


def generate_handle_table() -> str:
    return """CREATE TABLE handle (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    id TEXT NOT NULL,
    country TEXT,
    service TEXT NOT NULL,
    uncanonicalized_id TEXT,
    person_centric_id TEXT DEFAULT NULL,
    UNIQUE (id, service)
)"""


def generate_chat_table() -> str:
    return """CREATE TABLE chat (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT UNIQUE NOT NULL,
    style INTEGER,
    state INTEGER,
    account_id TEXT,
    properties BLOB,
    chat_identifier TEXT,
    service_name TEXT,
    room_name TEXT,
    account_login TEXT,
    is_archived INTEGER DEFAULT 0,
    last_addressed_handle TEXT,
    display_name TEXT,
    group_id TEXT,
    is_filtered INTEGER DEFAULT 0,
    successful_query INTEGER DEFAULT 1,
    engram_id TEXT,
    server_change_token TEXT,
    ck_sync_state INTEGER DEFAULT 0,
    last_read_message_timestamp INTEGER DEFAULT 0,
    original_group_id TEXT DEFAULT NULL,
    sr_server_change_token TEXT,
    sr_ck_sync_state INTEGER DEFAULT 0,
    cloudkit_record_id TEXT DEFAULT NULL,
    sr_cloudkit_record_id TEXT DEFAULT NULL,
    last_addressed_sim_id TEXT DEFAULT NULL,
    is_blackholed INTEGER DEFAULT 0,
    syndication_date INTEGER DEFAULT 0,
    syndication_type INTEGER DEFAULT 0,
    is_recovered INTEGER DEFAULT 0,
    is_deleting_incoming_messages INTEGER DEFAULT 0
)"""


def generate_deleted_messages_table() -> str:
    return """CREATE TABLE deleted_messages (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    guid TEXT NOT NULL
)"""


def generate_properties_table() -> str:
    return "CREATE TABLE _SqliteDatabaseProperties (key TEXT, value TEXT, UNIQUE(key))"


def generate_join_tables() -> dict[str, str]:
    return {
        "chat_handle_join": """CREATE TABLE chat_handle_join (
    chat_id INTEGER REFERENCES chat (ROWID) ON DELETE CASCADE,
    handle_id INTEGER REFERENCES handle (ROWID) ON DELETE CASCADE,
    UNIQUE(chat_id, handle_id)
)""",
        "chat_message_join": """CREATE TABLE chat_message_join (
    chat_id INTEGER REFERENCES chat (ROWID) ON DELETE CASCADE,
    message_id INTEGER REFERENCES message (ROWID) ON DELETE CASCADE,
    message_date INTEGER DEFAULT 0,
    PRIMARY KEY (chat_id, message_id)
)""",
        "message_attachment_join": """CREATE TABLE message_attachment_join (
    message_id INTEGER REFERENCES message (ROWID) ON DELETE CASCADE,
    attachment_id INTEGER REFERENCES attachment (ROWID) ON DELETE CASCADE,
    UNIQUE(message_id, attachment_id)
)""",
    }


def generate_sync_tables() -> dict[str, str]:
    return {
        "sync_deleted_messages": """CREATE TABLE sync_deleted_messages (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    guid TEXT NOT NULL,
    recordID TEXT
)""",
        "sync_deleted_chats": """CREATE TABLE sync_deleted_chats (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    guid TEXT NOT NULL,
    recordID TEXT,
    timestamp INTEGER
)""",
        "sync_deleted_attachments": """CREATE TABLE sync_deleted_attachments (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    guid TEXT NOT NULL,
    recordID TEXT
)""",
    }


def generate_recovery_tables() -> dict[str, str]:
    return {
        "chat_recoverable_message_join": """CREATE TABLE chat_recoverable_message_join (
    chat_id INTEGER REFERENCES chat (ROWID) ON DELETE CASCADE,
    message_id INTEGER REFERENCES message (ROWID) ON DELETE CASCADE,
    delete_date INTEGER,
    ck_sync_state INTEGER DEFAULT 0,
    PRIMARY KEY (chat_id, message_id),
    CHECK (delete_date != 0)
)""",
        "recoverable_message_part": """CREATE TABLE recoverable_message_part (
    chat_id INTEGER REFERENCES chat (ROWID) ON DELETE CASCADE,
    message_id INTEGER REFERENCES message (ROWID) ON DELETE CASCADE,
    part_index INTEGER,
    delete_date INTEGER,
    part_text BLOB NOT NULL,
    ck_sync_state INTEGER DEFAULT 0,
    PRIMARY KEY (chat_id, message_id, part_index),
    CHECK (delete_date != 0)
)""",
        "unsynced_removed_recoverable_messages": """CREATE TABLE unsynced_removed_recoverable_messages (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    chat_guid TEXT NOT NULL,
    message_guid TEXT NOT NULL,
    part_index INTEGER
)""",
    }


def generate_utility_tables() -> dict[str, str]:
    return {
        "kvtable": """CREATE TABLE kvtable (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    key TEXT UNIQUE NOT NULL,
    value BLOB NOT NULL
)""",
        "message_processing_task": """CREATE TABLE message_processing_task (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    guid TEXT NOT NULL,
    task_flags INTEGER NOT NULL
)""",
        "scheduled_messages_pending_cloudkit_delete": """CREATE TABLE scheduled_messages_pending_cloudkit_delete (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    guid TEXT NOT NULL,
    recordID TEXT
)""",
    }


def generate_common_indexes() -> list[str]:
    return [
        "CREATE INDEX chat_handle_join_idx_handle_id ON chat_handle_join(handle_id)",
        "CREATE INDEX chat_message_join_idx_chat_id ON chat_message_join(chat_id)",
        "CREATE INDEX chat_message_join_idx_message_id_only ON chat_message_join(message_id)",
        "CREATE INDEX chat_idx_is_archived ON chat(is_archived)",
        "CREATE INDEX chat_idx_chat_identifier ON chat(chat_identifier)",
        "CREATE INDEX chat_idx_chat_identifier_service_name ON chat(chat_identifier, service_name)",
        "CREATE INDEX chat_idx_chat_room_name_service_name ON chat(room_name, service_name)",
        "CREATE INDEX chat_idx_group_id ON chat(group_id)",
        "CREATE INDEX message_attachment_join_idx_attachment_id ON message_attachment_join(attachment_id)",
        "CREATE INDEX message_attachment_join_idx_message_id ON message_attachment_join(message_id)",
        "CREATE INDEX chat_recoverable_message_join_message_id_idx ON chat_recoverable_message_join(message_id)",
        "CREATE INDEX message_processing_task_idx_guid_task_flags ON message_processing_task(guid, task_flags)",
        "CREATE INDEX attachment_idx_is_sticker ON attachment(is_sticker)",
    ]
