"""DatabaseBuilder class for creating valid iMessage chat.db files."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from imessage_data_foundry.db.schema.base import (
    SchemaVersion,
    generate_message_guid,
)
from imessage_data_foundry.db.version_detect import (
    detect_schema_version,
    get_schema_for_version,
    get_schema_module,
)

if TYPE_CHECKING:
    from imessage_data_foundry.conversations.models import Attachment, Chat, Handle, Message
    from imessage_data_foundry.personas.models import Persona


class DatabaseBuilder:
    """Builder for creating valid iMessage SQLite databases.

    Usage:
        builder = DatabaseBuilder(output_path="./chat.db", version="sequoia")
        handle_id = builder.add_handle("+15551234567", service="iMessage")
        chat_id = builder.create_chat(handles=[handle_id], chat_type="direct")
        builder.add_message(chat_id, handle_id, "Hello!", is_from_me=False, date=ts)
        builder.finalize()

    Context manager usage:
        with DatabaseBuilder("./chat.db") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            builder.add_message(c, h, "Test", False, 1000000000)
        # Database is automatically finalized on exit
    """

    def __init__(
        self,
        output_path: str | Path,
        version: str | SchemaVersion | None = None,
        in_memory: bool = False,
    ) -> None:
        """Initialize the DatabaseBuilder.

        Args:
            output_path: Path where the database will be saved
            version: Schema version to use (auto-detected if None)
            in_memory: If True, build in memory then write on finalize()
        """
        self.output_path = Path(output_path)
        self.version = get_schema_for_version(version) if version else detect_schema_version()
        self.in_memory = in_memory

        self._connection: sqlite3.Connection | None = None
        self._finalized: bool = False

        # ID tracking (ROWID starts at 1)
        self._next_handle_rowid: int = 1
        self._next_chat_rowid: int = 1
        self._next_message_rowid: int = 1
        self._next_attachment_rowid: int = 1

        # GUID tracking for uniqueness validation
        self._message_guids: set[str] = set()
        self._chat_guids: set[str] = set()
        self._attachment_guids: set[str] = set()

        # Identifier -> ROWID mapping for deduplication
        self._handle_ids: dict[tuple[str, str], int] = {}  # (identifier, service) -> rowid
        self._chat_rowids: set[int] = set()

    @property
    def connection(self) -> sqlite3.Connection:
        """Get the database connection, initializing if needed."""
        if self._connection is None:
            self._initialize()
        return self._connection  # type: ignore[return-value]

    def _initialize(self) -> None:
        """Initialize the database with schema."""
        db_path = ":memory:" if self.in_memory else str(self.output_path)

        # Ensure parent directory exists for file-based databases
        if not self.in_memory:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            # Remove existing file to start fresh
            if self.output_path.exists():
                self.output_path.unlink()

        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row

        schema = get_schema_module(self.version)

        # Create tables
        for table_sql in schema.get_tables().values():
            self._connection.execute(table_sql)

        # Create indexes
        for index_sql in schema.get_indexes():
            self._connection.execute(index_sql)

        # Create triggers
        for trigger_sql in schema.get_triggers():
            self._connection.execute(trigger_sql)

        # Insert metadata
        metadata = schema.get_metadata()
        for key, value in metadata.items():
            self._connection.execute(
                "INSERT INTO _SqliteDatabaseProperties (key, value) VALUES (?, ?)",
                (key, str(value)),
            )

        self._connection.commit()

    def add_handle(
        self,
        identifier: str,
        service: str = "iMessage",
        country: str | None = "US",
        uncanonicalized_id: str | None = None,
    ) -> int:
        """Add a handle (contact) to the database.

        If a handle with the same identifier and service already exists,
        returns the existing ROWID.

        Args:
            identifier: Phone number (E.164) or email address
            service: "iMessage" or "SMS"
            country: Country code (e.g., "US")
            uncanonicalized_id: Original format before canonicalization

        Returns:
            The ROWID of the inserted or existing handle
        """
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
        """Add a handle from a Handle model."""
        return self.add_handle(
            identifier=handle.id,
            service=handle.service,
            country=handle.country,
            uncanonicalized_id=handle.uncanonicalized_id,
        )

    def add_handle_from_persona(self, persona: Persona) -> int:
        """Add a handle from a Persona model."""
        from imessage_data_foundry.conversations.models import Handle

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
        """Create a chat and link it to the given handles.

        Args:
            handles: List of handle ROWIDs to include in the chat
            chat_type: "direct" for 1:1, "group" for group chats
            service: "iMessage" or "SMS"
            display_name: Display name for group chats
            identifier: Chat identifier (auto-generated if None)

        Returns:
            The ROWID of the created chat
        """
        from uuid import uuid4

        rowid = self._next_chat_rowid
        self._next_chat_rowid += 1

        if chat_type == "direct":
            style = 43
            if identifier is None and handles:
                # Get the identifier from the first handle
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

        # Create chat_handle_join entries
        for handle_id in handles:
            self.connection.execute(
                "INSERT INTO chat_handle_join (chat_id, handle_id) VALUES (?, ?)",
                (rowid, handle_id),
            )

        self._chat_rowids.add(rowid)
        return rowid

    def create_chat_from_model(self, chat: Chat, handles: list[int]) -> int:
        """Create a chat from a Chat model."""
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
        """Add a message to the database.

        Args:
            chat_id: ROWID of the chat this message belongs to
            handle_id: ROWID of the sender handle (None for outgoing messages)
            text: Message text content
            is_from_me: True if sent by user, False if received
            date: Apple epoch nanoseconds timestamp
            service: "iMessage" or "SMS"
            guid: Message GUID (auto-generated if None)
            date_read: When message was read (Apple epoch ns)
            date_delivered: When message was delivered (Apple epoch ns)

        Returns:
            The ROWID of the inserted message

        Raises:
            ValueError: If guid is duplicate
        """
        if guid is None:
            guid = generate_message_guid()

        if guid in self._message_guids:
            raise ValueError(f"Duplicate message GUID: {guid}")
        self._message_guids.add(guid)

        rowid = self._next_message_rowid
        self._next_message_rowid += 1

        # For outgoing messages, handle_id should be 0
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
                1 if is_from_me else 0,  # is_sent
                1,  # is_delivered
                1 if not is_from_me else 0,  # is_read (received messages are read)
            ),
        )

        # Create chat_message_join entry
        self.connection.execute(
            "INSERT INTO chat_message_join (chat_id, message_id, message_date) VALUES (?, ?, ?)",
            (chat_id, rowid, date),
        )

        return rowid

    def add_message_from_model(self, message: Message, chat_id: int) -> int:
        """Add a message from a Message model."""
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
        """Add multiple messages in a batch for performance.

        Args:
            chat_id: ROWID of the chat
            messages: List of (handle_id, text, is_from_me, date) tuples
            service: Service for all messages

        Returns:
            List of inserted message ROWIDs
        """
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
        """Add an attachment to the database.

        Args:
            message_id: ROWID of the message this attachment belongs to
            filename: Path to attachment file
            uti: Uniform Type Identifier (e.g., "public.jpeg")
            mime_type: MIME type (e.g., "image/jpeg")
            total_bytes: File size in bytes
            is_outgoing: True if sent by user
            created_date: Creation timestamp (Apple epoch ns)
            guid: Attachment GUID (auto-generated if None)

        Returns:
            The ROWID of the inserted attachment
        """
        from uuid import uuid4

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

        # Create message_attachment_join entry
        self.connection.execute(
            "INSERT INTO message_attachment_join (message_id, attachment_id) VALUES (?, ?)",
            (message_id, rowid),
        )

        return rowid

    def add_attachment_from_model(self, attachment: Attachment, message_id: int) -> int:
        """Add an attachment from an Attachment model."""
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
        """Context manager for explicit transactions."""
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def commit(self) -> None:
        """Commit pending changes."""
        self.connection.commit()

    def finalize(self) -> Path:
        """Finalize the database and write to disk.

        Returns:
            The path to the finalized database
        """
        if self._finalized:
            raise RuntimeError("Database already finalized")

        self.connection.commit()

        if self.in_memory:
            # Copy in-memory database to file
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            file_conn = sqlite3.connect(str(self.output_path))
            self.connection.backup(file_conn)
            file_conn.close()

        self._finalized = True
        return self.output_path

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    @property
    def handle_count(self) -> int:
        """Number of handles added."""
        return len(self._handle_ids)

    @property
    def chat_count(self) -> int:
        """Number of chats created."""
        return len(self._chat_rowids)

    @property
    def message_count(self) -> int:
        """Number of messages added."""
        return len(self._message_guids)

    @property
    def attachment_count(self) -> int:
        """Number of attachments added."""
        return len(self._attachment_guids)

    def __enter__(self) -> DatabaseBuilder:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self._finalized and exc_type is None:
            self.finalize()
        self.close()
