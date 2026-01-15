import sqlite3
from pathlib import Path

from imessage_data_foundry.db.builder import DatabaseBuilder
from imessage_data_foundry.db.validators import (
    ValidationResult,
    get_all_indexes,
    get_all_tables,
    get_table_info,
    run_integrity_check,
    validate_database,
    validate_foreign_keys,
    validate_guid_uniqueness,
    validate_schema,
)


class TestValidationResult:
    def test_valid_is_truthy(self):
        result = ValidationResult(is_valid=True)
        assert result
        assert bool(result) is True

    def test_invalid_is_falsy(self):
        result = ValidationResult(is_valid=False)
        assert not result
        assert bool(result) is False

    def test_merge_valid_results(self):
        r1 = ValidationResult(is_valid=True, errors=[], warnings=["warn1"])
        r2 = ValidationResult(is_valid=True, errors=[], warnings=["warn2"])
        merged = r1.merge(r2)
        assert merged.is_valid
        assert merged.warnings == ["warn1", "warn2"]

    def test_merge_invalid_result(self):
        r1 = ValidationResult(is_valid=True, errors=[])
        r2 = ValidationResult(is_valid=False, errors=["error1"])
        merged = r1.merge(r2)
        assert not merged.is_valid
        assert "error1" in merged.errors


class TestGetTableInfo:
    def test_gets_columns(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            builder.add_handle("+15551234567")
            info = get_table_info(builder.connection, "handle")
            assert "id" in info.columns
            assert "service" in info.columns
            assert info.row_count == 1


class TestGetAllTables:
    def test_lists_all_tables(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia"):
            pass
        conn = sqlite3.connect(str(db_path))
        tables = get_all_tables(conn)
        conn.close()
        assert "message" in tables
        assert "handle" in tables
        assert "chat" in tables


class TestGetAllIndexes:
    def test_lists_indexes(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia"):
            pass
        conn = sqlite3.connect(str(db_path))
        indexes = get_all_indexes(conn)
        conn.close()
        assert len(indexes) > 0


class TestValidateSchema:
    def test_valid_database_passes(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            builder.add_handle("+15551234567")
        result = validate_schema(db_path)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_table_fails(self, tmp_path: Path):
        db_path = tmp_path / "broken.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE message (ROWID INTEGER PRIMARY KEY, guid TEXT)")
        conn.close()
        result = validate_schema(db_path)
        assert not result.is_valid
        assert any("Missing required table" in e for e in result.errors)

    def test_missing_column_fails(self, tmp_path: Path):
        db_path = tmp_path / "broken.db"
        conn = sqlite3.connect(str(db_path))
        # Create minimal tables but message missing required columns
        conn.execute("CREATE TABLE message (ROWID INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT, service TEXT)")
        conn.execute(
            "CREATE TABLE chat (ROWID INTEGER PRIMARY KEY, guid TEXT, style INTEGER, chat_identifier TEXT, service_name TEXT)"
        )
        conn.execute("CREATE TABLE attachment (ROWID INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE chat_handle_join (chat_id INTEGER, handle_id INTEGER)")
        conn.execute("CREATE TABLE chat_message_join (chat_id INTEGER, message_id INTEGER)")
        conn.execute(
            "CREATE TABLE message_attachment_join (message_id INTEGER, attachment_id INTEGER)"
        )
        conn.execute("CREATE TABLE _SqliteDatabaseProperties (key TEXT, value TEXT)")
        conn.execute("CREATE TABLE deleted_messages (ROWID INTEGER PRIMARY KEY, guid TEXT)")
        conn.close()
        result = validate_schema(db_path)
        assert not result.is_valid
        assert any("missing column" in e for e in result.errors)


class TestValidateForeignKeys:
    def test_valid_references_pass(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            builder.add_message(c, h, "Hello", is_from_me=False, date=1000)
        result = validate_foreign_keys(db_path)
        assert result.is_valid

    def test_orphaned_handle_fails(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            # Manually insert message with bad handle_id
            builder.connection.execute(
                """
                INSERT INTO message (ROWID, guid, text, handle_id, service, date, is_from_me)
                VALUES (99, 'bad-guid', 'Hello', 999, 'iMessage', 1000, 0)
                """
            )
            builder.connection.execute(
                "INSERT INTO chat_message_join (chat_id, message_id, message_date) VALUES (?, 99, 1000)",
                (c,),
            )
        result = validate_foreign_keys(db_path)
        assert not result.is_valid
        assert any("invalid handle_id" in e for e in result.errors)


class TestValidateGuidUniqueness:
    def test_unique_guids_pass(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            builder.add_message(c, h, "One", is_from_me=False, date=1000)
            builder.add_message(c, h, "Two", is_from_me=False, date=2000)
        result = validate_guid_uniqueness(db_path)
        assert result.is_valid

    def test_duplicate_message_guid_fails(self, tmp_path: Path):
        # Create a database without UNIQUE constraint on guid to test validator
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        # Create message table without UNIQUE on guid (normally it has UNIQUE)
        conn.execute(
            """
            CREATE TABLE message (
                ROWID INTEGER PRIMARY KEY,
                guid TEXT NOT NULL,
                text TEXT
            )
            """
        )
        conn.execute("CREATE TABLE chat (ROWID INTEGER PRIMARY KEY, guid TEXT)")
        conn.execute("CREATE TABLE attachment (ROWID INTEGER PRIMARY KEY, guid TEXT)")
        # Insert duplicate GUIDs
        conn.execute("INSERT INTO message (ROWID, guid, text) VALUES (1, 'dupe-guid', 'First')")
        conn.execute("INSERT INTO message (ROWID, guid, text) VALUES (2, 'dupe-guid', 'Second')")
        conn.commit()
        conn.close()
        result = validate_guid_uniqueness(db_path)
        assert not result.is_valid
        assert any("duplicate message GUIDs" in e for e in result.errors)


class TestValidateDatabase:
    def test_full_validation_passes(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            h = builder.add_handle("+15551234567")
            c = builder.create_chat([h])
            builder.add_message(c, h, "Hello", is_from_me=False, date=1000)
            builder.add_message(c, None, "Hi!", is_from_me=True, date=2000)
        result = validate_database(db_path)
        assert result.is_valid


class TestRunIntegrityCheck:
    def test_valid_database_passes(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with DatabaseBuilder(db_path, version="sequoia") as builder:
            builder.add_handle("+15551234567")
        result = run_integrity_check(db_path)
        assert result.is_valid
