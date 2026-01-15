from imessage_data_foundry.db.schema.base import (
    generate_chat_table,
    generate_common_indexes,
    generate_deleted_messages_table,
    generate_handle_table,
    generate_join_tables,
    generate_properties_table,
    generate_recovery_tables,
    generate_sync_tables,
    generate_utility_tables,
)

SCHEMA_VERSION: str = "sequoia"
MACOS_VERSIONS: list[str] = ["15.0", "15.1", "15.2", "15.3", "15.4", "15.5"]
CLIENT_VERSION: str = "18020"

MESSAGE_TABLE: str = """CREATE TABLE message (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT UNIQUE NOT NULL,
    text TEXT,
    replace INTEGER DEFAULT 0,
    service_center TEXT,
    handle_id INTEGER DEFAULT 0,
    subject TEXT,
    country TEXT,
    attributedBody BLOB,
    version INTEGER DEFAULT 0,
    type INTEGER DEFAULT 0,
    service TEXT,
    account TEXT,
    account_guid TEXT,
    error INTEGER DEFAULT 0,
    date INTEGER,
    date_read INTEGER,
    date_delivered INTEGER,
    is_delivered INTEGER DEFAULT 0,
    is_finished INTEGER DEFAULT 0,
    is_emote INTEGER DEFAULT 0,
    is_from_me INTEGER DEFAULT 0,
    is_empty INTEGER DEFAULT 0,
    is_delayed INTEGER DEFAULT 0,
    is_auto_reply INTEGER DEFAULT 0,
    is_prepared INTEGER DEFAULT 0,
    is_read INTEGER DEFAULT 0,
    is_system_message INTEGER DEFAULT 0,
    is_sent INTEGER DEFAULT 0,
    has_dd_results INTEGER DEFAULT 0,
    is_service_message INTEGER DEFAULT 0,
    is_forward INTEGER DEFAULT 0,
    was_downgraded INTEGER DEFAULT 0,
    is_archive INTEGER DEFAULT 0,
    cache_has_attachments INTEGER DEFAULT 0,
    cache_roomnames TEXT,
    was_data_detected INTEGER DEFAULT 0,
    was_deduplicated INTEGER DEFAULT 0,
    is_audio_message INTEGER DEFAULT 0,
    is_played INTEGER DEFAULT 0,
    date_played INTEGER,
    item_type INTEGER DEFAULT 0,
    other_handle INTEGER DEFAULT -1,
    group_title TEXT,
    group_action_type INTEGER DEFAULT 0,
    share_status INTEGER,
    share_direction INTEGER,
    is_expirable INTEGER DEFAULT 0,
    expire_state INTEGER DEFAULT 0,
    message_action_type INTEGER DEFAULT 0,
    message_source INTEGER DEFAULT 0,
    associated_message_guid TEXT DEFAULT NULL,
    balloon_bundle_id TEXT DEFAULT NULL,
    payload_data BLOB,
    associated_message_type INTEGER DEFAULT 0,
    expressive_send_style_id TEXT DEFAULT NULL,
    associated_message_range_location INTEGER DEFAULT 0,
    associated_message_range_length INTEGER DEFAULT 0,
    time_expressive_send_played INTEGER DEFAULT 0,
    message_summary_info BLOB DEFAULT NULL,
    ck_sync_state INTEGER DEFAULT 0,
    ck_record_id TEXT DEFAULT NULL,
    ck_record_change_tag TEXT DEFAULT NULL,
    destination_caller_id TEXT DEFAULT NULL,
    sr_ck_sync_state INTEGER DEFAULT 0,
    sr_ck_record_id TEXT DEFAULT NULL,
    sr_ck_record_change_tag TEXT DEFAULT NULL,
    is_corrupt INTEGER DEFAULT 0,
    reply_to_guid TEXT DEFAULT NULL,
    sort_id INTEGER DEFAULT 0,
    is_spam INTEGER DEFAULT 0,
    has_unseen_mention INTEGER DEFAULT 0,
    thread_originator_guid TEXT DEFAULT NULL,
    thread_originator_part TEXT DEFAULT NULL,
    syndication_ranges TEXT DEFAULT NULL,
    was_delivered_quietly INTEGER DEFAULT 0,
    did_notify_recipient INTEGER DEFAULT 0,
    synced_syndication_ranges TEXT DEFAULT NULL,
    date_retracted INTEGER DEFAULT 0,
    date_edited INTEGER DEFAULT 0,
    was_detonated INTEGER DEFAULT 0,
    part_count INTEGER,
    is_stewie INTEGER DEFAULT 0,
    is_kt_verified INTEGER DEFAULT 0,
    is_sos INTEGER DEFAULT 0,
    is_critical INTEGER DEFAULT 0,
    bia_reference_id TEXT DEFAULT NULL,
    fallback_hash TEXT DEFAULT NULL,
    associated_message_emoji TEXT DEFAULT NULL,
    is_pending_satellite_send INTEGER DEFAULT 0,
    needs_relay INTEGER DEFAULT 0,
    schedule_type INTEGER DEFAULT 0,
    schedule_state INTEGER DEFAULT 0,
    sent_or_received_off_grid INTEGER DEFAULT 0,
    date_recovered INTEGER DEFAULT 0
)"""

ATTACHMENT_TABLE: str = """CREATE TABLE attachment (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT UNIQUE NOT NULL,
    created_date INTEGER DEFAULT 0,
    start_date INTEGER DEFAULT 0,
    filename TEXT,
    uti TEXT,
    mime_type TEXT,
    transfer_state INTEGER DEFAULT 0,
    is_outgoing INTEGER DEFAULT 0,
    user_info BLOB,
    transfer_name TEXT,
    total_bytes INTEGER DEFAULT -1,
    is_sticker INTEGER DEFAULT 0,
    sticker_user_info BLOB,
    attribution_info BLOB,
    hide_attachment INTEGER DEFAULT 0,
    ck_sync_state INTEGER DEFAULT 0,
    ck_server_change_token_blob BLOB DEFAULT NULL,
    ck_record_id TEXT DEFAULT NULL,
    original_guid TEXT,
    sr_ck_record_id TEXT DEFAULT NULL,
    sr_ck_sync_state INTEGER DEFAULT 0,
    sr_ck_server_change_token_blob BLOB DEFAULT NULL,
    is_commsafety_sensitive INTEGER DEFAULT 0,
    emoji_image_content_identifier TEXT DEFAULT NULL,
    emoji_image_short_description TEXT DEFAULT NULL,
    preview_generation_state INTEGER DEFAULT 0
)"""


def get_tables() -> dict[str, str]:
    tables = {
        "_SqliteDatabaseProperties": generate_properties_table(),
        "handle": generate_handle_table(),
        "chat": generate_chat_table(),
        "message": MESSAGE_TABLE,
        "attachment": ATTACHMENT_TABLE,
        "deleted_messages": generate_deleted_messages_table(),
    }
    tables.update(generate_join_tables())
    tables.update(generate_sync_tables())
    tables.update(generate_recovery_tables())
    tables.update(generate_utility_tables())
    return tables


def get_indexes() -> list[str]:
    indexes = generate_common_indexes()
    indexes.extend(
        [
            "CREATE INDEX message_idx_failed ON message(is_finished, is_from_me, error)",
            "CREATE INDEX message_idx_handle ON message(handle_id, date)",
            "CREATE INDEX message_idx_is_read ON message(is_read, is_from_me, is_finished)",
            "CREATE INDEX message_idx_was_downgraded ON message(was_downgraded)",
            "CREATE INDEX message_idx_handle_id ON message(handle_id)",
            "CREATE INDEX message_idx_date ON message(date)",
            "CREATE INDEX message_idx_expire_state ON message(expire_state)",
            "CREATE INDEX message_idx_other_handle ON message(other_handle)",
            "CREATE INDEX message_idx_cache_has_attachments ON message(cache_has_attachments)",
            "CREATE INDEX message_idx_isRead_isFromMe_itemType ON message(is_read, is_from_me, item_type)",
            "CREATE INDEX message_idx_is_sent_is_from_me_error ON message(is_sent, is_from_me, error)",
            "CREATE INDEX message_idx_thread_originator_guid ON message(thread_originator_guid)",
            "CREATE INDEX message_idx_schedule_state ON message(schedule_state)",
            "CREATE INDEX chat_message_join_idx_message_date_id_chat_id ON chat_message_join(chat_id, message_date, message_id)",
            # Partial indexes
            "CREATE INDEX attachment_idx_purged_attachments_v2 ON attachment(hide_attachment, ck_sync_state, transfer_state) WHERE hide_attachment=0 AND (ck_sync_state=1 OR ck_sync_state=4) AND transfer_state=0",
            "CREATE INDEX message_idx_undelivered_one_to_one_imessage ON message(cache_roomnames, service, is_sent, is_delivered, was_downgraded, item_type) WHERE cache_roomnames IS NULL AND service IN ('iMessage','RCS') AND is_sent = 1 AND is_delivered = 0 AND was_downgraded = 0 AND item_type = 0 AND schedule_type = 0",
            "CREATE INDEX message_idx_is_pending_satellite_message ON message(is_pending_satellite_send) WHERE is_pending_satellite_send=1",
            "CREATE INDEX message_idx_is_scheduled_message ON message(schedule_type) WHERE schedule_type=2",
            "CREATE INDEX message_idx_fallback_hash ON message(fallback_hash) WHERE fallback_hash IS NOT NULL",
            "CREATE INDEX message_idx_associated_message2 ON message(associated_message_guid) WHERE associated_message_guid IS NOT NULL",
        ]
    )
    return indexes


def get_triggers() -> list[str]:
    return [
        """CREATE TRIGGER after_insert_on_chat_message_join AFTER INSERT ON chat_message_join BEGIN
    UPDATE message
      SET cache_roomnames = (
        SELECT group_concat(c.room_name)
        FROM chat c
        INNER JOIN chat_message_join j ON c.ROWID = j.chat_id
        WHERE j.message_id = NEW.message_id
      )
      WHERE message.ROWID = NEW.message_id;
END""",
        """CREATE TRIGGER after_insert_on_message_attachment_join AFTER INSERT ON message_attachment_join BEGIN
    UPDATE message SET cache_has_attachments = 1 WHERE message.ROWID = NEW.message_id;
END""",
        """CREATE TRIGGER update_message_date_after_update_on_message AFTER UPDATE OF date ON message BEGIN
    UPDATE chat_message_join SET message_date = NEW.date WHERE message_id = NEW.ROWID AND message_date != NEW.date;
END""",
        """CREATE TRIGGER add_to_deleted_messages AFTER DELETE ON message BEGIN
    INSERT INTO deleted_messages (guid) VALUES (OLD.guid);
END""",
        """CREATE TRIGGER add_to_sync_deleted_messages AFTER DELETE ON message BEGIN
    INSERT INTO sync_deleted_messages (guid, recordID) VALUES (OLD.guid, OLD.ck_record_id);
END""",
        """CREATE TRIGGER add_to_sync_deleted_attachments AFTER DELETE ON attachment BEGIN
    INSERT INTO sync_deleted_attachments (guid, recordID) VALUES (OLD.guid, OLD.ck_record_id);
END""",
    ]


def get_metadata() -> dict[str, str]:
    return {
        "_ClientVersion": CLIENT_VERSION,
        "counter_in_all": "0",
        "counter_out_all": "0",
        "counter_in_lifetime": "0",
        "counter_out_lifetime": "0",
        "counter_last_reset": "0",
    }
