# ARCHITECTURE.md — Technical Design

## Project Structure

```
imessage-data-foundry/
├── pyproject.toml              # uv project configuration
├── README.md                   # Project overview
├── OBJECTIVE.md                # Project goals and requirements
├── ARCHITECTURE.md             # This file
├── Makefile                    # Build/test utilities
│
├── imessage_data_foundry/
│   ├── __init__.py
│   ├── __main__.py             # Entry point
│   ├── app.py                  # Textual TUI application
│   ├── cli.py                  # Optional CLI interface
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema/
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # Common schema elements
│   │   │   ├── sonoma.py       # macOS 14 Sonoma schema
│   │   │   ├── sequoia.py      # macOS 15 Sequoia schema
│   │   │   └── tahoe.py        # macOS 26 Tahoe schema
│   │   ├── builder.py          # Database construction logic
│   │   ├── validators.py       # Schema validation
│   │   └── version_detect.py   # macOS version detection
│   │
│   ├── personas/
│   │   ├── __init__.py
│   │   ├── models.py           # Persona data models
│   │   ├── storage.py          # Persona SQLite persistence
│   │   ├── generator.py        # LLM-based persona generation
│   │   └── library.py          # Persona library management
│   │
│   ├── conversations/
│   │   ├── __init__.py
│   │   ├── models.py           # Conversation/message models
│   │   ├── generator.py        # LLM conversation generation
│   │   ├── timestamps.py       # Realistic timestamp generation
│   │   └── seeding.py          # Conversation seed handling
│   │
│   ├── attachments/
│   │   ├── __init__.py
│   │   ├── generator.py        # Placeholder attachment creation
│   │   └── stubs/              # Template placeholder files
│   │       ├── placeholder.png
│   │       ├── placeholder.jpg
│   │       └── placeholder.heic
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract LLM interface
│   │   ├── openai_provider.py  # OpenAI implementation
│   │   ├── anthropic_provider.py # Anthropic implementation
│   │   └── prompts.py          # Prompt templates
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── screens/
│   │   │   ├── __init__.py
│   │   │   ├── welcome.py
│   │   │   ├── config.py
│   │   │   ├── personas.py
│   │   │   ├── conversations.py
│   │   │   └── generation.py
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── persona_card.py
│   │   │   ├── chat_preview.py
│   │   │   └── progress.py
│   │   └── styles.tcss         # Textual CSS styling
│   │
│   └── utils/
│       ├── __init__.py
│       ├── apple_time.py       # Apple epoch timestamp handling
│       └── phone_numbers.py    # Phone number formatting
│
├── data/
│   └── foundry.db              # Local persona library database
│
├── tests/
│   ├── __init__.py
│   ├── test_schema.py
│   ├── test_personas.py
│   ├── test_conversations.py
│   └── fixtures/
│       └── sample_chat.db      # Reference database for testing
│
└── docs/
    └── schema_reference.md     # iMessage schema documentation
```

## Core Data Models

### Persona Model

```python
@dataclass
class Persona:
    id: str                     # UUID
    name: str                   # Display name
    identifier: str             # Phone number or email
    identifier_type: str        # "phone" or "email"
    country_code: str           # e.g., "US"
    
    # Personality attributes
    personality: str            # Personality description
    writing_style: str          # How they write (formal, casual, etc.)
    relationship: str           # Relationship to "self" (friend, family, etc.)
    
    # Behavioral attributes
    communication_frequency: str  # "high", "medium", "low"
    typical_response_time: str    # "instant", "minutes", "hours", "days"
    emoji_usage: str              # "none", "light", "moderate", "heavy"
    vocabulary_level: str         # "simple", "moderate", "sophisticated"
    topics_of_interest: list[str] # Topics they like to discuss
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    is_self: bool               # True if this is the user's persona
```

### Conversation Configuration

```python
@dataclass
class ConversationConfig:
    id: str                     # UUID
    name: str                   # Optional chat name (for groups)
    participants: list[str]     # Persona IDs
    chat_type: str              # "direct" or "group"
    
    # Generation parameters
    message_count_target: int   # Target number of messages
    time_range_start: datetime  # When conversation begins
    time_range_end: datetime    # When conversation ends
    seed: str | None            # Optional conversation seed/theme
    
    # Service type
    service: str                # "iMessage" or "SMS"
```

## Database Schema Strategy

### Version Detection

```python
def detect_macos_version() -> str:
    """
    Detect current macOS version and return schema identifier.
    Returns: "sonoma" | "sequoia" | "tahoe"
    Falls back to "sequoia" if detection fails or not on macOS.
    """
```

### Schema Abstraction

Each schema version module exports:

```python
# Example: schema/sonoma.py

SCHEMA_VERSION = "sonoma"
MACOS_VERSIONS = ["14.0", "14.1", "14.2", ...]

# Complete CREATE TABLE statements
TABLES: dict[str, str] = {
    "message": """
        CREATE TABLE message (
            ROWID INTEGER PRIMARY KEY AUTOINCREMENT,
            guid TEXT UNIQUE NOT NULL,
            text TEXT,
            ...
        )
    """,
    "handle": "...",
    "chat": "...",
    # ... all tables
}

# Required indexes
INDEXES: list[str] = [...]

# Required triggers (if any)
TRIGGERS: list[str] = [...]

# Schema metadata table content
METADATA: dict[str, Any] = {
    "_SqliteDatabaseProperties": {...}
}
```

### Core Tables (Common Across Versions)

| Table | Purpose |
|-------|---------|
| `message` | Individual messages |
| `handle` | Contact identifiers (phone/email) |
| `chat` | Conversation threads |
| `attachment` | File attachments |
| `chat_handle_join` | Links chats to participants |
| `chat_message_join` | Links chats to messages |
| `message_attachment_join` | Links messages to attachments |
| `deleted_messages` | Tombstones for deleted messages |
| `_SqliteDatabaseProperties` | Schema metadata |

## LLM Integration

### Provider Interface

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def generate_persona(self, constraints: dict) -> Persona:
        """Generate a new persona based on constraints."""
        pass
    
    @abstractmethod
    async def generate_messages(
        self,
        personas: list[Persona],
        context: ConversationContext,
        count: int
    ) -> list[Message]:
        """Generate a batch of messages for a conversation."""
        pass
    
    @abstractmethod
    async def approve_persona(self, persona: Persona) -> Persona:
        """Present persona for user approval, return modified version."""
        pass
```

### Conversation Generation Strategy

1. **Batch Generation** — Generate messages in batches of 20-50 to maintain context
2. **Context Window** — Include last 10-20 messages as context for continuity
3. **Persona Grounding** — Each generation call includes full persona descriptions
4. **Timestamp Assignment** — Timestamps assigned post-generation using realistic distribution

### Prompt Templates

```python
PERSONA_GENERATION_PROMPT = """
Create a realistic person who would be a {relationship} of someone.

Consider:
- A distinctive name
- Communication style and vocabulary
- Personality traits that affect texting behavior
- Topics they'd naturally discuss
- Emoji and slang usage patterns

{additional_constraints}

Respond with a JSON object matching the Persona schema.
"""

CONVERSATION_PROMPT = """
You are simulating a text message conversation between these people:

{persona_descriptions}

Current conversation context:
{recent_messages}

{seed_context}

Generate the next {count} messages in this conversation.
Each message should:
- Match the sender's personality and writing style
- Flow naturally from previous messages
- Feel like genuine text messages (varying lengths, casual tone)

Respond with a JSON array of messages.
"""
```

## Timestamp Generation

### Realistic Distribution Algorithm

```python
def generate_timestamps(
    start: datetime,
    end: datetime,
    count: int,
    personas: list[Persona]
) -> list[datetime]:
    """
    Generate realistic message timestamps with:
    - Batched conversations (flurries of messages)
    - Gaps between conversation sessions
    - Time-of-day awareness (fewer messages at 3am)
    - Response time variation based on persona settings
    """
```

Key characteristics:
- **Conversation Sessions**: 70% of messages in clustered "sessions" of 5-30 messages
- **Inter-session Gaps**: Hours to days between sessions
- **Circadian Rhythm**: Weighted toward waking hours (8am-11pm)
- **Response Delays**: Based on persona's `typical_response_time`

## Persona Library Storage

### Schema for `foundry.db`

```sql
CREATE TABLE personas (
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
    topics_of_interest TEXT,  -- JSON array
    is_self INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE generation_history (
    id TEXT PRIMARY KEY,
    output_path TEXT NOT NULL,
    macos_version TEXT NOT NULL,
    persona_ids TEXT NOT NULL,  -- JSON array
    message_count INTEGER,
    created_at TEXT NOT NULL
);
```

## Error Handling Strategy

1. **Graceful Degradation** — If LLM fails, offer retry or manual input
2. **Validation Checkpoints** — Validate data at each stage before DB insertion
3. **Transaction Safety** — Use SQLite transactions for atomic writes
4. **Progress Persistence** — Save generation progress to allow resume on failure

## Performance Considerations

- **Async LLM Calls** — Use asyncio for parallel message generation
- **Batch Inserts** — Insert messages in batches of 100-500
- **Progress Streaming** — Stream progress updates to TUI during generation
- **Memory Management** — Process large conversations in chunks to avoid memory issues

## Testing Strategy

1. **Schema Tests** — Verify generated schemas match reference databases
2. **Integration Tests** — Test full generation pipeline with mock LLM
3. **Compatibility Tests** — Validate output with `imessage-exporter` tool
4. **Persona Tests** — Verify persona CRUD operations
5. **Timestamp Tests** — Validate realistic distribution properties
