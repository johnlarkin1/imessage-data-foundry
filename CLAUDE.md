# CLAUDE.md — Implementation Guide for Claude Code

This file provides context and guidance for implementing iMessage Data Foundry using Claude Code.

## Project Context

This is a Python tool that generates fake iMessage SQLite databases with realistic AI-generated conversations. The databases exactly replicate the macOS `chat.db` schema for testing/development purposes. As a reminder, keep the code simple and don't use too many comments. Limit entrypoints and hidden abstraction.

## Key Documents

1. **docs/OBJECTIVE.md** — Project goals, requirements, and scope
2. **docs/ARCHITECTURE.md** — Technical design, project structure, data models
3. **docs/SCHEMA_NOTES.md** — iMessage database schema reference
4. **README.md** — User-facing documentation
5. **pyproject.toml** — Dependencies and project configuration

## Implementation Order

### Phase 1: Foundation

1. **Set up project structure** — Create all directories from ARCHITECTURE.md
2. **Implement Apple timestamp utilities** — `imessage_data_foundry/utils/apple_time.py`
3. **Implement phone number utilities** — `imessage_data_foundry/utils/phone_numbers.py`
4. **Create Pydantic models** for Persona and Conversation — `imessage_data_foundry/personas/models.py`

### Phase 2: Database Layer

1. **Define base schema** — Common elements across all versions
2. **Implement Sequoia schema first** — Most common current version
3. **Create DatabaseBuilder class** — Handles creation of valid `chat.db`
4. **Add schema validation** — Verify generated DBs match expected structure
5. **Add version detection** — Auto-detect macOS version

### Phase 3: Persona System

1. **Implement persona storage** — SQLite-based persistence in `foundry.db`
2. **Create persona CRUD operations** — Add, edit, delete, list
3. **Add persona library management** — Load/save persona sets

### Phase 4: LLM Integration

1. **Define abstract LLM provider interface** — `imessage_data_foundry/llm/base.py`
2. **Implement OpenAI provider** — Using `openai` SDK
3. **Implement Anthropic provider** — Using `anthropic` SDK
4. **Create prompt templates** — For persona and conversation generation

### Phase 5: Conversation Generation

1. **Implement timestamp generator** — Realistic distribution algorithm
2. **Create conversation generator** — Orchestrates LLM calls
3. **Add conversation seeding** — Optional themes/seeds
4. **Implement batch generation** — Handle large message counts

### Phase 6: TUI Application

1. **Create main Textual app** — `imessage_data_foundry/app.py`
2. **Implement welcome/config screen**
3. **Implement persona management screen**
4. **Implement conversation setup screen**
5. **Implement generation progress screen**
6. **Add styling** — `imessage_data_foundry/ui/styles.tcss`

### Phase 7: Polish & Testing

1. **Add comprehensive tests**
2. **Test with `imessage-exporter`** — Validate compatibility
3. **Add error handling and recovery**
4. **Performance optimization** — Batch inserts, async LLM calls

## Key Technical Decisions

### Database Builder Pattern

```python
# Example usage pattern to implement
builder = DatabaseBuilder(version="sequoia", output_path="./output/chat.db")
builder.add_handle("+15551234567", service="iMessage")
builder.add_handle("+15559876543", service="iMessage")
chat_id = builder.create_chat(handles=[1, 2], chat_type="direct")
builder.add_message(chat_id, handle_id=1, text="Hey!", is_from_me=False, date=timestamp)
builder.add_message(chat_id, handle_id=None, text="Hi there!", is_from_me=True, date=timestamp2)
builder.finalize()  # Writes to disk, creates indexes
```

### LLM Conversation Generation

```python
# Generate messages in batches to maintain context
async def generate_conversation(
    personas: list[Persona],
    config: ConversationConfig,
    provider: LLMProvider
) -> list[Message]:
    messages = []
    batch_size = 30

    while len(messages) < config.message_count_target:
        context = messages[-15:]  # Last 15 for context
        batch = await provider.generate_messages(
            personas=personas,
            context=context,
            count=min(batch_size, config.message_count_target - len(messages)),
            seed=config.seed
        )
        messages.extend(batch)

    # Assign realistic timestamps post-generation
    timestamps = generate_timestamps(
        start=config.time_range_start,
        end=config.time_range_end,
        count=len(messages),
        personas=personas
    )

    for msg, ts in zip(messages, timestamps):
        msg.date = ts

    return messages
```

### Timestamp Distribution

Implement a realistic timestamp generator that:

- Creates "conversation sessions" (clusters of rapid messages)
- Adds natural gaps between sessions (hours to days)
- Weights toward waking hours (8am-11pm)
- Varies response times based on persona settings

```python
def generate_timestamps(start, end, count, personas):
    # 1. Divide time range into potential session slots
    # 2. Randomly select ~70% of messages to be in sessions
    # 3. Create 5-30 message clusters with rapid-fire timing (30s - 5min gaps)
    # 4. Distribute remaining 30% as scattered messages
    # 5. Apply circadian weighting
    # 6. Sort chronologically
    pass
```

## Testing Strategy

### Schema Validation Test

```python
def test_generated_schema_matches_reference():
    """Compare generated DB schema against known-good reference."""
    builder = DatabaseBuilder(version="sequoia", output_path=":memory:")
    builder.initialize_schema()

    generated_tables = get_table_schemas(builder.connection)
    reference_tables = get_table_schemas(load_reference_db())

    for table_name in reference_tables:
        assert table_name in generated_tables
        assert generated_tables[table_name] == reference_tables[table_name]
```

### Compatibility Test

```python
def test_compatible_with_imessage_exporter():
    """Verify output works with imessage-exporter tool."""
    # Generate a test database
    # Run imessage-exporter against it
    # Verify no errors and output is produced
    pass
```

## Common Pitfalls to Avoid

1. **Foreign key integrity** — Always create handles before messages, chats before joins
2. **GUID uniqueness** — Every message/attachment needs a unique GUID
3. **Timestamp format** — Apple uses nanoseconds since Jan 1, 2001
4. **Join table completeness** — Messages without `chat_message_join` entries won't appear
5. **Service consistency** — `handle.service`, `chat.service_name`, `message.service` must align

## Environment Variables

```bash
# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Custom config directory (foundry.db created in this path's parent)
IMESSAGE_FOUNDRY_CONFIG=~/.config/imessage-data-foundry/config
```

## Useful Commands During Development

Use `make` commands for common development tasks:

```bash
# Run the app
make run

# Run tests
make test

# Type checking only
make check

# Format code
make fmt

# Lint (includes ruff check, format check, and mypy)
make lint

# Inspect a generated database
sqlite3 ./output/chat.db ".schema"
sqlite3 ./output/chat.db "SELECT * FROM message LIMIT 10"

# Compare with real iMessage DB (requires Full Disk Access)
sqlite3 ~/Library/Messages/chat.db ".schema message"
```

## Schema Research Commands

When researching schema differences between macOS versions:

```bash
# Dump schema from real chat.db
sqlite3 ~/Library/Messages/chat.db ".schema" > schema_dump.sql

# List all tables
sqlite3 ~/Library/Messages/chat.db ".tables"

# Get table info
sqlite3 ~/Library/Messages/chat.db "PRAGMA table_info(message)"

# Get indexes
sqlite3 ~/Library/Messages/chat.db ".indexes message"
```

## Notes for Claude Code

### Code Style Rules

- **No top-level file docstrings** — Don't add module-level docstrings at the start of files
- **Minimal comments** — Code should be self-explanatory; only comment non-obvious logic
- **No `from __future__ import annotations`** — Use `typing.Self` for forward self-references instead
- **All imports at top of module** — No inline imports inside functions or methods
- **No re-exports in `__init__.py`** — Import directly from source modules to avoid circular imports
- **Run `make lint` before committing** — Must pass ruff check, ruff format, and mypy

### Import Guidelines

```python
# GOOD: Import directly from source
from imessage_data_foundry.conversations.generator import ConversationGenerator

# BAD: Import from package __init__.py re-export
from imessage_data_foundry.conversations import ConversationGenerator
```

### Technical Guidelines

- **Start with the database layer** — Everything else depends on it
- **Use `imessage-exporter` source code as schema reference** — It's the most complete
- **Test incrementally** — Verify each phase before moving to the next
- **Keep schemas as pure SQL strings** — Easier to diff and validate
- **Use Pydantic for all data models** — Type safety and validation
- **Async for LLM calls** — Better UX with progress updates
