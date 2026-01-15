import sqlite3
from pathlib import Path

import pytest

from imessage_data_foundry.db.builder import DatabaseBuilder
from imessage_data_foundry.db.schema.base import SchemaVersion


class TestDatabaseBuilderInit:
    def test_default_version_detection(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        builder = DatabaseBuilder(db_path)
        assert builder.version in [SchemaVersion.SONOMA, SchemaVersion.SEQUOIA, SchemaVersion.TAHOE]
        builder.close()

    def test_explicit_version(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        builder = DatabaseBuilder(db_path, version="sonoma")
        assert builder.version == SchemaVersion.SONOMA
        builder.close()

    def test_creates_parent_directory(self, tmp_path: Path):
        db_path = tmp_path / "subdir" / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            builder.add_handle("+15551234567")
        assert db_path.exists()


class TestDatabaseBuilderContextManager:
    def test_creates_database_file(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia"):
            pass
        assert db_path.exists()

    def test_finalizes_on_exit(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            builder.add_handle("+15551234567")
        # Verify we can open the database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM handle")
        assert cursor.fetchone()[0] == 1
        conn.close()


class TestAddHandle:
    def test_returns_rowid(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            handle_id = builder.add_handle("+15551234567")
            assert handle_id == 1

    def test_increments_rowid(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h1 = builder.add_handle("+15551234567")
            h2 = builder.add_handle("+15559876543")
            assert h1 == 1
            assert h2 == 2

    def test_deduplicates_same_identifier(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h1 = builder.add_handle("+15551234567", service="iMessage")
            h2 = builder.add_handle("+15551234567", service="iMessage")
            assert h1 == h2

    def test_different_service_creates_new(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h1 = builder.add_handle("+15551234567", service="iMessage")
            h2 = builder.add_handle("+15551234567", service="SMS")
            assert h1 != h2

    def test_verifies_in_database(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            builder.add_handle("+15551234567", service="iMessage", country="US")
            cursor = builder.connection.execute(
                "SELECT id, service, country FROM handle WHERE ROWID = 1"
            )
            row = cursor.fetchone()
            assert row["id"] == "+15551234567"
            assert row["service"] == "iMessage"
            assert row["country"] == "US"


class TestCreateChat:
    def test_returns_rowid(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            chat_id = builder.create_chat([h])
            assert chat_id == 1

    def test_direct_chat_style(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            chat_id = builder.create_chat([h], chat_type="direct")
            cursor = builder.connection.execute(
                "SELECT style FROM chat WHERE ROWID = ?", (chat_id,)
            )
            assert cursor.fetchone()["style"] == 43

    def test_group_chat_style(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h1 = builder.add_handle("+15551234567")
            h2 = builder.add_handle("+15559876543")
            chat_id = builder.create_chat([h1, h2], chat_type="group")
            cursor = builder.connection.execute(
                "SELECT style FROM chat WHERE ROWID = ?", (chat_id,)
            )
            assert cursor.fetchone()["style"] == 45

    def test_creates_chat_handle_join(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h1 = builder.add_handle("+15551234567")
            h2 = builder.add_handle("+15559876543")
            chat_id = builder.create_chat([h1, h2])
            cursor = builder.connection.execute(
                "SELECT handle_id FROM chat_handle_join WHERE chat_id = ?",
                (chat_id,),
            )
            handles = [row["handle_id"] for row in cursor.fetchall()]
            assert h1 in handles
            assert h2 in handles

    def test_direct_chat_guid_format(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            chat_id = builder.create_chat([h], chat_type="direct", service="iMessage")
            cursor = builder.connection.execute("SELECT guid FROM chat WHERE ROWID = ?", (chat_id,))
            guid = cursor.fetchone()["guid"]
            assert guid == "iMessage;-;+15551234567"


class TestAddMessage:
    def test_returns_rowid(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            msg_id = builder.add_message(c, h, "Hello!", is_from_me=False, date=1000)
            assert msg_id == 1

    def test_creates_chat_message_join(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            msg_id = builder.add_message(c, h, "Hello!", is_from_me=False, date=1000)
            cursor = builder.connection.execute(
                "SELECT chat_id, message_date FROM chat_message_join WHERE message_id = ?",
                (msg_id,),
            )
            row = cursor.fetchone()
            assert row["chat_id"] == c
            assert row["message_date"] == 1000

    def test_outgoing_message_has_zero_handle_id(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            msg_id = builder.add_message(c, None, "Hello!", is_from_me=True, date=1000)
            cursor = builder.connection.execute(
                "SELECT handle_id, is_from_me FROM message WHERE ROWID = ?",
                (msg_id,),
            )
            row = cursor.fetchone()
            assert row["handle_id"] == 0
            assert row["is_from_me"] == 1

    def test_incoming_message_has_handle_id(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            msg_id = builder.add_message(c, h, "Hello!", is_from_me=False, date=1000)
            cursor = builder.connection.execute(
                "SELECT handle_id, is_from_me FROM message WHERE ROWID = ?",
                (msg_id,),
            )
            row = cursor.fetchone()
            assert row["handle_id"] == h
            assert row["is_from_me"] == 0

    def test_duplicate_guid_raises(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            guid = "p:0/test-guid-123"
            builder.add_message(c, h, "First", is_from_me=False, date=1000, guid=guid)
            with pytest.raises(ValueError, match="Duplicate message GUID"):
                builder.add_message(c, h, "Second", is_from_me=False, date=2000, guid=guid)


class TestAddMessagesBatch:
    def test_returns_rowids(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            messages = [
                (h, "Hello", False, 1000),
                (None, "Hi there", True, 2000),
                (h, "How are you?", False, 3000),
            ]
            rowids = builder.add_messages_batch(c, messages)
            assert len(rowids) == 3
            assert rowids == [1, 2, 3]

    def test_all_messages_in_database(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            messages = [
                (h, "Message 1", False, 1000),
                (None, "Message 2", True, 2000),
            ]
            builder.add_messages_batch(c, messages)
            cursor = builder.connection.execute("SELECT COUNT(*) FROM message")
            assert cursor.fetchone()[0] == 2


class TestAddAttachment:
    def test_returns_rowid(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            m = builder.add_message(c, h, "Check this out", is_from_me=False, date=1000)
            att_id = builder.add_attachment(m, filename="image.jpg")
            assert att_id == 1

    def test_creates_message_attachment_join(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            m = builder.add_message(c, h, "Check this out", is_from_me=False, date=1000)
            att_id = builder.add_attachment(m, filename="image.jpg")
            cursor = builder.connection.execute(
                "SELECT message_id FROM message_attachment_join WHERE attachment_id = ?",
                (att_id,),
            )
            assert cursor.fetchone()["message_id"] == m


class TestInMemoryBuilder:
    def test_builds_in_memory_then_writes(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia", in_memory=True) as builder:
            builder.add_handle("+15551234567")
            # File shouldn't exist yet during building
        # File should exist after context manager exits
        assert db_path.exists()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM handle")
        assert cursor.fetchone()[0] == 1
        conn.close()


class TestBuilderCounts:
    def test_handle_count(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            builder.add_handle("+15551234567")
            builder.add_handle("+15559876543")
            assert builder.handle_count == 2

    def test_message_count(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            builder.add_message(c, h, "One", is_from_me=False, date=1000)
            builder.add_message(c, h, "Two", is_from_me=False, date=2000)
            builder.add_message(c, None, "Three", is_from_me=True, date=3000)
            assert builder.message_count == 3

    def test_chat_count(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h1 = builder.add_handle("+15551234567")
            h2 = builder.add_handle("+15559876543")
            builder.create_chat([h1])
            builder.create_chat([h2])
            assert builder.chat_count == 2
