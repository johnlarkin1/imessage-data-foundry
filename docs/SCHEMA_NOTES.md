# SCHEMA_NOTES.md — iMessage Database Schema Reference

## Overview

The iMessage database (`chat.db`) is located at `~/Library/Messages/chat.db` on macOS. It's a SQLite database that stores all message history, contacts, and attachments metadata.

## Important: Apple Epoch Timestamps

Apple uses a custom epoch for timestamps: **January 1, 2001 00:00:00 UTC**

Conversion formulas:
```python
# Apple timestamp to Unix timestamp
unix_ts = apple_ts + 978307200

# Unix timestamp to Apple timestamp  
apple_ts = unix_ts - 978307200

# Note: Modern versions use nanoseconds
apple_ts_ns = apple_ts * 1_000_000_000
```

## Core Tables

### `handle`

Stores contact identifiers (phone numbers or email addresses).

```sql
CREATE TABLE handle (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL,              -- Phone number or email (e.g., "+15551234567")
    country TEXT,                  -- Country code (e.g., "US")
    service TEXT NOT NULL,         -- "iMessage" or "SMS"
    uncanonicalized_id TEXT,       -- Original format before canonicalization
    person_centric_id TEXT         -- Links to contact card
);
```

### `chat`

Represents conversation threads (both 1:1 and group).

```sql
CREATE TABLE chat (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL UNIQUE,     -- Unique identifier (e.g., "iMessage;-;+15551234567")
    style INTEGER,                 -- 43 = 1:1, 45 = group chat
    state INTEGER,                 -- Chat state
    account_id TEXT,               -- Account used
    properties BLOB,               -- Plist blob with additional properties
    chat_identifier TEXT,          -- Primary identifier
    service_name TEXT,             -- "iMessage" or "SMS"
    room_name TEXT,                -- Group chat name (if set)
    account_login TEXT,            -- Login for account
    is_archived INTEGER DEFAULT 0,
    last_addressed_handle TEXT,
    display_name TEXT,             -- Display name for group chats
    group_id TEXT,
    is_filtered INTEGER DEFAULT 0,
    successful_query INTEGER DEFAULT 0,
    engram_id TEXT,
    server_change_token TEXT,
    ck_sync_state INTEGER DEFAULT 0,
    original_group_id TEXT,
    last_read_message_timestamp INTEGER DEFAULT 0,
    sr_server_change_token TEXT,
    sr_ck_sync_state INTEGER DEFAULT 0,
    cloudkit_record_id TEXT,
    sr_cloudkit_record_id TEXT,
    last_addressed_sim_id TEXT,
    is_blackholed INTEGER DEFAULT 0,
    syndication_date INTEGER DEFAULT 0,
    syndication_type INTEGER DEFAULT 0,
    is_recovered INTEGER DEFAULT 0,
    is_deleting_incoming_messages INTEGER DEFAULT 0
);
```

### `message`

Individual messages — the largest and most complex table.

```sql
CREATE TABLE message (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL UNIQUE,
    text TEXT,                     -- Message text content
    replace INTEGER DEFAULT 0,
    service_center TEXT,
    handle_id INTEGER DEFAULT 0,   -- FK to handle.ROWID
    subject TEXT,
    country TEXT,
    attributedBody BLOB,           -- Rich text content (NSAttributedString)
    version INTEGER DEFAULT 0,
    type INTEGER DEFAULT 0,
    service TEXT,                  -- "iMessage" or "SMS"
    account TEXT,
    account_guid TEXT,
    error INTEGER DEFAULT 0,
    date INTEGER,                  -- Apple epoch nanoseconds
    date_read INTEGER,
    date_delivered INTEGER,
    is_delivered INTEGER DEFAULT 0,
    is_finished INTEGER DEFAULT 0,
    is_emote INTEGER DEFAULT 0,
    is_from_me INTEGER DEFAULT 0,  -- 1 if sent by user, 0 if received
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
    other_handle INTEGER DEFAULT 0,
    group_title TEXT,
    group_action_type INTEGER DEFAULT 0,
    share_status INTEGER DEFAULT 0,
    share_direction INTEGER DEFAULT 0,
    is_expirable INTEGER DEFAULT 0,
    expire_state INTEGER DEFAULT 0,
    message_action_type INTEGER DEFAULT 0,
    message_source INTEGER DEFAULT 0,
    associated_message_guid TEXT,
    associated_message_type INTEGER DEFAULT 0,
    balloon_bundle_id TEXT,
    payload_data BLOB,
    expressive_send_style_id TEXT,
    associated_message_range_location INTEGER DEFAULT 0,
    associated_message_range_length INTEGER DEFAULT 0,
    time_expressive_send_played INTEGER,
    message_summary_info BLOB,
    ck_sync_state INTEGER DEFAULT 0,
    ck_record_id TEXT,
    ck_record_change_tag TEXT,
    destination_caller_id TEXT,
    sr_ck_sync_state INTEGER DEFAULT 0,
    sr_ck_record_id TEXT,
    sr_ck_record_change_tag TEXT,
    is_corrupt INTEGER DEFAULT 0,
    reply_to_guid TEXT,
    sort_id INTEGER,
    is_spam INTEGER DEFAULT 0,
    has_unseen_mention INTEGER DEFAULT 0,
    thread_originator_guid TEXT,
    thread_originator_part TEXT,
    syndication_ranges TEXT,
    synced_syndication_ranges TEXT,
    was_delivered_quietly INTEGER DEFAULT 0,
    did_notify_recipient INTEGER DEFAULT 0,
    date_retracted INTEGER DEFAULT 0,
    date_edited INTEGER DEFAULT 0,
    was_detonated INTEGER DEFAULT 0,
    part_count INTEGER DEFAULT 1,
    is_stewie INTEGER DEFAULT 0,
    is_kt_verified INTEGER DEFAULT 0,
    is_sos INTEGER DEFAULT 0,
    is_critical INTEGER DEFAULT 0,
    bia_reference_id TEXT,
    fallback_hash TEXT
);
```

### `attachment`

Metadata for file attachments.

```sql
CREATE TABLE attachment (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL UNIQUE,
    created_date INTEGER,          -- Apple epoch
    start_date INTEGER,
    filename TEXT,                 -- Path relative to ~/Library/Messages/Attachments/
    uti TEXT,                      -- Uniform Type Identifier (e.g., "public.jpeg")
    mime_type TEXT,                -- MIME type
    transfer_state INTEGER DEFAULT 0,
    is_outgoing INTEGER DEFAULT 0,
    user_info BLOB,
    transfer_name TEXT,
    total_bytes INTEGER DEFAULT 0,
    is_sticker INTEGER DEFAULT 0,
    sticker_user_info BLOB,
    attribution_info BLOB,
    hide_attachment INTEGER DEFAULT 0,
    ck_sync_state INTEGER DEFAULT 0,
    ck_server_change_token_blob BLOB,
    ck_record_id TEXT,
    original_guid TEXT,
    sr_ck_sync_state INTEGER DEFAULT 0,
    sr_ck_server_change_token_blob BLOB,
    sr_ck_record_id TEXT,
    is_commsafety_sensitive INTEGER DEFAULT 0,
    emoji_image_short_description TEXT,
    emoji_image_localized_description BLOB
);
```

### Join Tables

```sql
-- Links chats to their participants
CREATE TABLE chat_handle_join (
    chat_id INTEGER REFERENCES chat(ROWID),
    handle_id INTEGER REFERENCES handle(ROWID),
    UNIQUE(chat_id, handle_id)
);

-- Links chats to their messages
CREATE TABLE chat_message_join (
    chat_id INTEGER REFERENCES chat(ROWID),
    message_id INTEGER REFERENCES message(ROWID),
    message_date INTEGER,          -- Denormalized for query performance
    UNIQUE(chat_id, message_id)
);

-- Links messages to their attachments
CREATE TABLE message_attachment_join (
    message_id INTEGER REFERENCES message(ROWID),
    attachment_id INTEGER REFERENCES attachment(ROWID),
    UNIQUE(message_id, attachment_id)
);
```

### Metadata Table

```sql
CREATE TABLE _SqliteDatabaseProperties (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Typical contents:
-- _ClientVersion: "14003" (varies by macOS version)
-- _DateCreated: timestamp
-- _UniqueIdentifier: UUID
```

### `deleted_messages`

Tombstones for deleted messages.

```sql
CREATE TABLE deleted_messages (
    ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL UNIQUE
);
```

## Version-Specific Differences

### Research Needed

The schema has evolved across macOS versions. Key areas to investigate:

| Version | Changes to Research |
|---------|---------------------|
| Sonoma (14.x) | Baseline schema |
| Sequoia (15.x) | New columns? Index changes? |
| Tahoe (26.x) | Potential major changes |

### Known Evolution Points

- `attributedBody` field usage has changed — newer versions store more text there
- `reply_to_guid` and thread fields added in later versions
- `is_stewie`, `is_kt_verified`, `is_sos`, `is_critical` are newer additions
- Attachment schema expanded for stickers and emoji

## GUID Formats

### Chat GUIDs

```
iMessage;-;+15551234567              # 1:1 iMessage
iMessage;+;chat123456789             # Group iMessage
SMS;-;+15551234567                   # 1:1 SMS
```

### Message GUIDs

```
# Format varies, typically UUID-based
p:0/E3B0C442-98FC-1C14-B39F-F32D3E0CFA04
```

### Attachment GUIDs

```
# Usually matches a pattern with message reference
at_0_E3B0C442-98FC-1C14-B39F-F32D3E0CFA04
```

## Indexes

Key indexes for query performance:

```sql
CREATE INDEX message_idx_handle ON message(handle_id);
CREATE INDEX message_idx_date ON message(date);
CREATE INDEX message_idx_is_from_me ON message(is_from_me);
CREATE INDEX chat_message_join_idx_message_id ON chat_message_join(message_id);
CREATE INDEX chat_message_join_idx_chat_id ON chat_message_join(chat_id);
-- ... many more
```

## Implementation Notes

### Generating Valid Data

1. **GUIDs must be unique** — Use UUID4 for message/attachment GUIDs
2. **Handle IDs must exist** — Create handles before messages
3. **Join tables are critical** — Messages won't appear in chats without proper joins
4. **Timestamps must be consistent** — `date` < `date_delivered` < `date_read`

### Minimal Valid Message

```python
{
    "guid": str(uuid4()),
    "text": "Hello!",
    "handle_id": 1,  # Must exist in handle table
    "service": "iMessage",
    "date": apple_timestamp_ns,
    "is_from_me": 0,
    "is_sent": 0,
    "is_delivered": 1,
    "is_read": 1,
    "is_finished": 1,
}
```

### Minimal Valid Chat

```python
{
    "guid": f"iMessage;-;+15551234567",
    "style": 43,  # 1:1 chat
    "chat_identifier": "+15551234567",
    "service_name": "iMessage",
    "state": 3,
}
```

## Resources

- [imessage-exporter source](https://github.com/ReagentX/imessage-exporter) — Best reference for schema
- [SQLiteFlow](https://www.sqliteflow.com/) — Useful for exploring real databases
- Apple's plist format documentation for `properties` and `attributedBody` blobs
