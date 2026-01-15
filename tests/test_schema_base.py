from imessage_data_foundry.db.schema.base import (
    SchemaVersion,
    generate_attachment_guid,
    generate_chat_guid,
    generate_chat_table,
    generate_deleted_messages_table,
    generate_handle_table,
    generate_join_tables,
    generate_message_guid,
    generate_properties_table,
)


class TestSchemaVersion:
    def test_sonoma_value(self):
        assert SchemaVersion.SONOMA.value == "sonoma"

    def test_sequoia_value(self):
        assert SchemaVersion.SEQUOIA.value == "sequoia"

    def test_tahoe_value(self):
        assert SchemaVersion.TAHOE.value == "tahoe"

    def test_from_string(self):
        assert SchemaVersion("sequoia") == SchemaVersion.SEQUOIA


class TestGenerateMessageGuid:
    def test_format(self):
        guid = generate_message_guid()
        assert guid.startswith("p:0/")
        assert len(guid) > 10

    def test_uniqueness(self):
        guids = {generate_message_guid() for _ in range(1000)}
        assert len(guids) == 1000


class TestGenerateChatGuid:
    def test_direct_imessage(self):
        guid = generate_chat_guid("iMessage", "direct", "+15551234567")
        assert guid == "iMessage;-;+15551234567"

    def test_direct_sms(self):
        guid = generate_chat_guid("SMS", "direct", "+15551234567")
        assert guid == "SMS;-;+15551234567"

    def test_group_imessage(self):
        guid = generate_chat_guid("iMessage", "group", "chat123abc")
        assert guid == "iMessage;+;chat123abc"

    def test_email_identifier(self):
        guid = generate_chat_guid("iMessage", "direct", "user@example.com")
        assert guid == "iMessage;-;user@example.com"


class TestGenerateAttachmentGuid:
    def test_format(self):
        guid = generate_attachment_guid()
        assert guid.startswith("at_0_")
        assert len(guid) > 10

    def test_uniqueness(self):
        guids = {generate_attachment_guid() for _ in range(1000)}
        assert len(guids) == 1000


class TestGenerateHandleTable:
    def test_contains_create_table(self):
        sql = generate_handle_table()
        assert "CREATE TABLE handle" in sql

    def test_has_rowid(self):
        sql = generate_handle_table()
        assert "ROWID INTEGER PRIMARY KEY" in sql

    def test_has_required_columns(self):
        sql = generate_handle_table()
        assert "id TEXT NOT NULL" in sql
        assert "service TEXT NOT NULL" in sql
        assert "country TEXT" in sql


class TestGenerateChatTable:
    def test_contains_create_table(self):
        sql = generate_chat_table()
        assert "CREATE TABLE chat" in sql

    def test_has_required_columns(self):
        sql = generate_chat_table()
        assert "guid TEXT UNIQUE NOT NULL" in sql
        assert "style INTEGER" in sql
        assert "chat_identifier TEXT" in sql
        assert "service_name TEXT" in sql


class TestGenerateJoinTables:
    def test_returns_all_joins(self):
        tables = generate_join_tables()
        assert "chat_handle_join" in tables
        assert "chat_message_join" in tables
        assert "message_attachment_join" in tables

    def test_chat_handle_join_structure(self):
        tables = generate_join_tables()
        sql = tables["chat_handle_join"]
        assert "chat_id INTEGER" in sql
        assert "handle_id INTEGER" in sql
        assert "REFERENCES chat" in sql
        assert "REFERENCES handle" in sql

    def test_chat_message_join_has_date(self):
        tables = generate_join_tables()
        sql = tables["chat_message_join"]
        assert "message_date INTEGER" in sql


class TestGenerateDeletedMessagesTable:
    def test_structure(self):
        sql = generate_deleted_messages_table()
        assert "CREATE TABLE deleted_messages" in sql
        assert "guid TEXT NOT NULL" in sql


class TestGeneratePropertiesTable:
    def test_structure(self):
        sql = generate_properties_table()
        assert "CREATE TABLE _SqliteDatabaseProperties" in sql
        assert "key TEXT" in sql
        assert "value TEXT" in sql
