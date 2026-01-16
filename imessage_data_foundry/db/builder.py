import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Self
from uuid import uuid4

from imessage_data_foundry.conversations.models import Attachment, Chat, Handle, Message
from imessage_data_foundry.db.schema.base import (
    SchemaVersion,
    generate_message_guid,
)
from imessage_data_foundry.db.version_detect import (
    detect_schema_version,
    get_schema_for_version,
    get_schema_module,
)
from imessage_data_foundry.personas.models import Persona


class DatabaseBuilder:
    def __init__(
        self,
        output_path: str | Path,
        version: str | SchemaVersion | None = None,
        in_memory: bool = False,
        append: bool = False,
    ) -> None:
        self.output_path = Path(output_path)
        self.version = get_schema_for_version(version) if version else detect_schema_version()
        self.in_memory = in_memory
        self.append = append

        self._connection: sqlite3.Connection | None = None
        self._finalized: bool = False

        self._next_handle_rowid: int = 1
        self._next_chat_rowid: int = 1
        self._next_message_rowid: int = 1
        self._next_attachment_rowid: int = 1

        self._message_guids: set[str] = set()
        self._chat_guids: set[str] = set()
        self._attachment_guids: set[str] = set()

        self._handle_ids: dict[tuple[str, str], int] = {}
        self._chat_rowids: set[int] = set()

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._initialize()
        return self._connection  # type: ignore[return-value]

    def _initialize(self) -> None:
        db_path = ":memory:" if self.in_memory else str(self.output_path)

        if not self.in_memory:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.append and self.output_path.exists() and not self.in_memory:
            self._connection = sqlite3.connect(db_path)
            self._connection.row_factory = sqlite3.Row
            self._load_existing_state()
        else:
            self._connection = sqlite3.connect(db_path)
            self._connection.row_factory = sqlite3.Row
            self._create_schema()

    def _create_schema(self) -> None:
        schema = get_schema_module(self.version)

        for table_sql in schema.get_tables().values():
            self.connection.execute(table_sql)
        for index_sql in schema.get_indexes():
            self.connection.execute(index_sql)
        for trigger_sql in schema.get_triggers():
            self.connection.execute(trigger_sql)

        metadata = schema.get_metadata()
        for key, value in metadata.items():
            self.connection.execute(
                "INSERT INTO _SqliteDatabaseProperties (key, value) VALUES (?, ?)",
                (key, str(value)),
            )

        self.connection.commit()

    def _load_existing_state(self) -> None:
        cursor = self.connection.execute("SELECT MAX(ROWID) FROM handle")
        max_handle = cursor.fetchone()[0]
        self._next_handle_rowid = (max_handle or 0) + 1

        cursor = self.connection.execute("SELECT MAX(ROWID) FROM chat")
        max_chat = cursor.fetchone()[0]
        self._next_chat_rowid = (max_chat or 0) + 1

        cursor = self.connection.execute("SELECT MAX(ROWID) FROM message")
        max_message = cursor.fetchone()[0]
        self._next_message_rowid = (max_message or 0) + 1

        cursor = self.connection.execute("SELECT MAX(ROWID) FROM attachment")
        max_attachment = cursor.fetchone()[0]
        self._next_attachment_rowid = (max_attachment or 0) + 1

        cursor = self.connection.execute("SELECT guid FROM message")
        self._message_guids = {row[0] for row in cursor.fetchall()}

        cursor = self.connection.execute("SELECT guid FROM chat")
        self._chat_guids = {row[0] for row in cursor.fetchall()}

        cursor = self.connection.execute("SELECT guid FROM attachment")
        self._attachment_guids = {row[0] for row in cursor.fetchall()}

        cursor = self.connection.execute("SELECT ROWID, id, service FROM handle")
        for row in cursor.fetchall():
            self._handle_ids[(row[1], row[2])] = row[0]

        cursor = self.connection.execute("SELECT ROWID FROM chat")
        self._chat_rowids = {row[0] for row in cursor.fetchall()}

    def add_handle(
        self,
        identifier: str,
        service: str = "iMessage",
        country: str | None = "US",
        uncanonicalized_id: str | None = None,
    ) -> int:
        key = (identifier, service)
        if key in self._handle_ids:
            return self._handle_ids[key]

        rowid = self._next_handle_rowid
        self._next_handle_rowid += 1

        self.connection.execute(
            """
            INSERT INTO handle (ROWID, id, country, service, uncanonicalized_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (rowid, identifier, country, service, uncanonicalized_id),
        )
        self._handle_ids[key] = rowid
        return rowid

    def add_handle_from_model(self, handle: Handle) -> int:
        return self.add_handle(
            identifier=handle.id,
            service=handle.service,
            country=handle.country,
            uncanonicalized_id=handle.uncanonicalized_id,
        )

    def add_handle_from_persona(self, persona: Persona) -> int:
        handle = Handle.from_persona(persona)
        return self.add_handle_from_model(handle)

    def create_chat(
        self,
        handles: list[int],
        chat_type: str = "direct",
        service: str = "iMessage",
        display_name: str | None = None,
        identifier: str | None = None,
    ) -> int:
        rowid = self._next_chat_rowid
        self._next_chat_rowid += 1

        if chat_type == "direct":
            style = 43
            if identifier is None and handles:
                cursor = self.connection.execute(
                    "SELECT id FROM handle WHERE ROWID = ?",
                    (handles[0],),
                )
                row = cursor.fetchone()
                identifier = row["id"] if row else f"unknown-{rowid}"
            elif identifier is None:
                identifier = f"unknown-{rowid}"
            guid = f"{service};-;{identifier}"
        else:
            style = 45
            if identifier is None:
                identifier = f"chat{uuid4().hex[:12]}"
            guid = f"{service};+;{identifier}"

        if guid in self._chat_guids:
            raise ValueError(f"Duplicate chat GUID: {guid}")
        self._chat_guids.add(guid)

        self.connection.execute(
            """
            INSERT INTO chat (ROWID, guid, style, state, chat_identifier,
                              service_name, display_name)
            VALUES (?, ?, ?, 3, ?, ?, ?)
            """,
            (rowid, guid, style, identifier, service, display_name),
        )

        for handle_id in handles:
            self.connection.execute(
                "INSERT INTO chat_handle_join (chat_id, handle_id) VALUES (?, ?)",
                (rowid, handle_id),
            )

        self._chat_rowids.add(rowid)
        return rowid

    def create_chat_from_model(self, chat: Chat, handles: list[int]) -> int:
        chat_type = "direct" if chat.style == 43 else "group"
        return self.create_chat(
            handles=handles,
            chat_type=chat_type,
            service=chat.service_name,
            display_name=chat.display_name,
            identifier=chat.chat_identifier,
        )

    def add_message(
        self,
        chat_id: int,
        handle_id: int | None,
        text: str,
        is_from_me: bool,
        date: int,
        service: str = "iMessage",
        guid: str | None = None,
        date_read: int | None = None,
        date_delivered: int | None = None,
    ) -> int:
        if guid is None:
            guid = generate_message_guid()

        if guid in self._message_guids:
            raise ValueError(f"Duplicate message GUID: {guid}")
        self._message_guids.add(guid)

        rowid = self._next_message_rowid
        self._next_message_rowid += 1
        db_handle_id = 0 if is_from_me else (handle_id or 0)

        self.connection.execute(
            """
            INSERT INTO message (
                ROWID, guid, text, handle_id, service, date,
                date_read, date_delivered, is_from_me, is_sent,
                is_delivered, is_read, is_finished
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                rowid,
                guid,
                text,
                db_handle_id,
                service,
                date,
                date_read,
                date_delivered,
                1 if is_from_me else 0,
                1 if is_from_me else 0,
                1,
                1 if not is_from_me else 0,
            ),
        )
        self.connection.execute(
            "INSERT INTO chat_message_join (chat_id, message_id, message_date) VALUES (?, ?, ?)",
            (chat_id, rowid, date),
        )
        return rowid

    def add_message_from_model(self, message: Message, chat_id: int) -> int:
        return self.add_message(
            chat_id=chat_id,
            handle_id=message.handle_id,
            text=message.text or "",
            is_from_me=message.is_from_me,
            date=message.date,
            service=message.service,
            guid=message.guid,
            date_read=message.date_read,
            date_delivered=message.date_delivered,
        )

    def add_messages_batch(
        self,
        chat_id: int,
        messages: list[tuple[int | None, str, bool, int]],
        service: str = "iMessage",
    ) -> list[int]:
        rowids = []
        message_data = []
        join_data = []

        for handle_id, text, is_from_me, date in messages:
            guid = generate_message_guid()
            if guid in self._message_guids:
                raise ValueError(f"Duplicate message GUID: {guid}")
            self._message_guids.add(guid)

            rowid = self._next_message_rowid
            self._next_message_rowid += 1
            rowids.append(rowid)

            db_handle_id = 0 if is_from_me else (handle_id or 0)

            message_data.append(
                (
                    rowid,
                    guid,
                    text,
                    db_handle_id,
                    service,
                    date,
                    1 if is_from_me else 0,
                    1 if is_from_me else 0,
                    1,
                    1 if not is_from_me else 0,
                )
            )

            join_data.append((chat_id, rowid, date))

        self.connection.executemany(
            """
            INSERT INTO message (
                ROWID, guid, text, handle_id, service, date,
                is_from_me, is_sent, is_delivered, is_read, is_finished
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            message_data,
        )

        self.connection.executemany(
            "INSERT INTO chat_message_join (chat_id, message_id, message_date) VALUES (?, ?, ?)",
            join_data,
        )

        return rowids

    def add_attachment(
        self,
        message_id: int,
        filename: str | None = None,
        uti: str | None = None,
        mime_type: str | None = None,
        total_bytes: int = 0,
        is_outgoing: bool = False,
        created_date: int | None = None,
        guid: str | None = None,
    ) -> int:
        if guid is None:
            guid = f"at_0_{uuid4()!s}"

        if guid in self._attachment_guids:
            raise ValueError(f"Duplicate attachment GUID: {guid}")
        self._attachment_guids.add(guid)

        rowid = self._next_attachment_rowid
        self._next_attachment_rowid += 1

        self.connection.execute(
            """
            INSERT INTO attachment (
                ROWID, guid, filename, uti, mime_type, total_bytes,
                is_outgoing, created_date, transfer_state
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 5)
            """,
            (
                rowid,
                guid,
                filename,
                uti,
                mime_type,
                total_bytes,
                1 if is_outgoing else 0,
                created_date,
            ),
        )
        self.connection.execute(
            "INSERT INTO message_attachment_join (message_id, attachment_id) VALUES (?, ?)",
            (message_id, rowid),
        )
        return rowid

    def add_attachment_from_model(self, attachment: Attachment, message_id: int) -> int:
        return self.add_attachment(
            message_id=message_id,
            filename=attachment.filename,
            uti=attachment.uti,
            mime_type=attachment.mime_type,
            total_bytes=attachment.total_bytes,
            is_outgoing=attachment.is_outgoing,
            created_date=attachment.created_date,
            guid=attachment.guid,
        )

    @contextmanager
    def transaction(self):
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def commit(self) -> None:
        self.connection.commit()

    def finalize(self) -> Path:
        if self._finalized:
            raise RuntimeError("Database already finalized")

        self.connection.commit()

        if self.in_memory:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            file_conn = sqlite3.connect(str(self.output_path))
            self.connection.backup(file_conn)
            file_conn.close()

        self._finalized = True
        return self.output_path

    def close(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None

    @property
    def handle_count(self) -> int:
        return len(self._handle_ids)

    @property
    def chat_count(self) -> int:
        return len(self._chat_rowids)

    @property
    def message_count(self) -> int:
        return len(self._message_guids)

    @property
    def attachment_count(self) -> int:
        return len(self._attachment_guids)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self._finalized and exc_type is None:
            self.finalize()
        self.close()
