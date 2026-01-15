SCHEMA = """
CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    identifier TEXT NOT NULL,
    identifier_type TEXT NOT NULL,
    country_code TEXT DEFAULT 'US',
    personality TEXT,
    writing_style TEXT,
    relationship TEXT,
    communication_frequency TEXT,
    typical_response_time TEXT,
    emoji_usage TEXT,
    vocabulary_level TEXT,
    topics_of_interest TEXT,
    is_self INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generation_history (
    id TEXT PRIMARY KEY,
    output_path TEXT NOT NULL,
    macos_version TEXT NOT NULL,
    persona_ids TEXT NOT NULL,
    message_count INTEGER,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_personas_name ON personas(name);
CREATE INDEX IF NOT EXISTS idx_personas_is_self ON personas(is_self);
CREATE INDEX IF NOT EXISTS idx_personas_identifier ON personas(identifier);
"""

INSERT_PERSONA = """
    INSERT INTO personas (
        id, name, identifier, identifier_type, country_code,
        personality, writing_style, relationship,
        communication_frequency, typical_response_time,
        emoji_usage, vocabulary_level, topics_of_interest,
        is_self, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

SELECT_BY_ID = "SELECT * FROM personas WHERE id = ?"
SELECT_BY_NAME = "SELECT * FROM personas WHERE name LIKE ? ORDER BY name"
SELECT_SELF = "SELECT * FROM personas WHERE is_self = 1 LIMIT 1"
SELECT_ALL = "SELECT * FROM personas ORDER BY name"
SELECT_COUNT = "SELECT COUNT(*) FROM personas"
SELECT_EXISTS = "SELECT 1 FROM personas WHERE id = ?"

UPDATE_PERSONA = """
    UPDATE personas SET
        name = ?, identifier = ?, identifier_type = ?, country_code = ?,
        personality = ?, writing_style = ?, relationship = ?,
        communication_frequency = ?, typical_response_time = ?,
        emoji_usage = ?, vocabulary_level = ?, topics_of_interest = ?,
        is_self = ?, updated_at = ?
    WHERE id = ?
"""

DELETE_BY_ID = "DELETE FROM personas WHERE id = ?"
DELETE_ALL = "DELETE FROM personas"
