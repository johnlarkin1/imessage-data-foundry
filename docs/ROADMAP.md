# ROADMAP.md — Implementation Plan

## Current State

- ✅ Project scaffolding (pyproject.toml, basic entry points)
- ✅ Documentation (OBJECTIVE.md, ARCHITECTURE.md, SCHEMA_NOTES.md, CLAUDE.md)
- ✅ **Phase 1: Foundation & Utilities** — Complete
- ✅ **Phase 2: Database Layer** — Complete
- ✅ **Phase 3: Persona System** — Complete
- ✅ **Phase 4: LLM Integration** — Complete
- ✅ **Phase 5: Conversation Generation** — Complete
- 🔲 Phase 6: TUI Application — **Up Next**
- 🔲 Phase 7: Testing & Polish

---

## ✅ Phase 1: Foundation & Utilities (COMPLETE)

**Goal:** Create the building blocks that everything else depends on.

| Task | File | Status | Description |
|------|------|--------|-------------|
| 1.1 | `utils/apple_time.py` | ✅ | Apple epoch ↔ Unix timestamp conversion (nanoseconds) |
| 1.2 | `utils/phone_numbers.py` | ✅ | Phone number formatting, validation, country codes |
| 1.3 | `personas/models.py` | ✅ | Pydantic models for Persona, ConversationConfig |
| 1.4 | `conversations/models.py` | ✅ | Pydantic models for Message, Chat, Handle, Attachment |

**Deliverables:**
- 7 timestamp conversion functions
- 8 phone number utility functions
- 7 enums (IdentifierType, CommunicationFrequency, ResponseTime, etc.)
- 4 Pydantic models with full validation
- 83 tests with 90% code coverage
- Makefile with lint/fmt/test/run targets

---

## 🔲 Phase 2: Database Layer (UP NEXT)

**Goal:** Generate valid `chat.db` files that pass schema validation.

| Task | File | Description |
|------|------|-------------|
| 2.1 | `db/schema/base.py` | Common schema elements, table definitions |
| 2.2 | `db/schema/sequoia.py` | macOS 15 Sequoia schema (primary target) |
| 2.3 | `db/version_detect.py` | Auto-detect macOS version |
| 2.4 | `db/builder.py` | DatabaseBuilder class - creates valid databases |
| 2.5 | `db/validators.py` | Schema validation against reference |
| 2.6 | `db/schema/sonoma.py` | macOS 14 Sonoma schema |
| 2.7 | `db/schema/tahoe.py` | macOS 26 Tahoe schema (placeholder) |

**Critical insight:** The DatabaseBuilder is the heart of the project. A working builder with just Sequoia support unlocks all downstream work.

**Validation checkpoint:** Generate a DB and verify with:
```bash
sqlite3 ./output/chat.db ".schema"
sqlite3 ~/Library/Messages/chat.db ".schema" | diff - <(sqlite3 ./output/chat.db ".schema")
```

---

## ✅ Phase 3: Persona System (COMPLETE)

**Goal:** Create, store, and manage personas for conversation generation.

| Task | File | Status | Description |
|------|------|--------|-------------|
| 3.1 | `personas/storage.py` | ✅ | SQLite persistence for personas (foundry.db) |
| 3.2 | `personas/storage.py` | ✅ | CRUD operations, import/export (merged into storage) |
| 3.3 | `personas/generator.py` | 🔲 | LLM-based persona generation (deferred to Phase 4) |

**Deliverables:**
- `PersonaStorage` class (240 lines) - full CRUD, batch ops, export/import
- `PersonaNotFoundError` exception for error handling
- `get_default_db_path()` with cascading defaults (env → ~/.config → ./data)
- Schema: `personas` table + `generation_history` table with indexes
- 37 tests with 96% code coverage
- Context manager support for clean resource handling

**Capabilities:**
- Create/read/update/delete personas
- Query by ID, name (partial match), or is_self flag
- Batch create and delete operations
- Export all personas to JSON
- Import personas from JSON (with optional replace mode)

**Example Usage:**
```python
from imessage_data_foundry.personas import PersonaStorage, Persona

with PersonaStorage() as storage:
    # Create
    persona = Persona(name="Alice", identifier="+15551234567")
    storage.create(persona)

    # Query
    alice = storage.get_by_name("Alice")[0]
    me = storage.get_self()
    all_personas = storage.list_all()

    # Export/Import
    data = storage.export_all()
    storage.import_personas(data, replace=True)
```

---

## ✅ Phase 4: LLM Integration (COMPLETE)

**Goal:** Abstract interface for persona and message generation with local MLX models as default.

| Task | File | Status | Description |
|------|------|--------|-------------|
| 4.1 | `llm/config.py` | ✅ | LLMConfig with pydantic-settings, RAM auto-detection |
| 4.2 | `llm/models.py` | ✅ | PersonaConstraints, GeneratedMessage, GeneratedPersona |
| 4.3 | `llm/base.py` | ✅ | Abstract LLMProvider interface |
| 4.4 | `llm/prompts.py` | ✅ | Prompt templates for persona/conversation generation |
| 4.5 | `llm/local_provider.py` | ✅ | Local MLX provider (default, no API key required) |
| 4.6 | `llm/openai_provider.py` | ✅ | OpenAI GPT implementation |
| 4.7 | `llm/anthropic_provider.py` | ✅ | Anthropic Claude implementation |
| 4.8 | `llm/manager.py` | ✅ | ProviderManager with fallback logic |

**Deliverables:**
- `LocalMLXProvider` - Default provider using mlx-lm on Apple Silicon (no API key required)
- `OpenAIProvider` - Optional cloud provider (requires OPENAI_API_KEY)
- `AnthropicProvider` - Optional cloud provider (requires ANTHROPIC_API_KEY)
- `ProviderManager` - Automatic provider selection with fallback chain
- Auto-detection of system RAM for optimal model selection:
  - 8GB RAM → Llama-3.2-3B-Instruct-4bit
  - 16GB+ RAM → Qwen3-4B-Instruct-4bit
  - 24GB+ RAM → Qwen3-8B-Instruct-4bit
- 65 tests with comprehensive coverage

**Capabilities:**
- Generate personas with constraints (relationship, vocabulary, topics, etc.)
- Generate conversation messages in batches
- Stream messages for progress feedback
- Automatic JSON parsing with validation
- Lazy model loading for fast startup

**Example Usage:**
```python
from imessage_data_foundry.llm import ProviderManager, PersonaConstraints

async def generate():
    manager = ProviderManager()
    provider = await manager.get_provider()  # Auto-selects best available

    # Generate personas
    constraints = PersonaConstraints(relationship="friend", vocabulary_level="moderate")
    personas = await provider.generate_personas(constraints, count=2)

    # Generate messages
    messages = await provider.generate_messages(
        persona_descriptions=[...],
        context=[],
        count=30,
        seed="planning a weekend trip"
    )
```

---

## ✅ Phase 5: Conversation Generation (COMPLETE)

**Goal:** Generate realistic message threads with proper timestamps.

| Task | File | Status | Description |
|------|------|--------|-------------|
| 5.1 | `conversations/timestamps.py` | ✅ | Realistic timestamp distribution algorithm |
| 5.2 | `conversations/generator.py` | ✅ | Orchestrates LLM calls, batch generation |
| 5.3 | `conversations/seeding.py` | ✅ | Conversation themes/seeds handling |

**Deliverables:**
- `ConversationGenerator` class (~340 lines) - async batch generation with progress callbacks
- `generate_timestamps()` function (~250 lines) - realistic timestamp distribution
- `TimestampedMessage` dataclass - wraps GeneratedMessage with timestamp
- 67 tests covering all components

**Timestamp Algorithm:**
- Session clustering: ~70% of messages in rapid-fire clusters (5-30 messages)
- Circadian weighting: Peak messaging 18:00-21:00, minimal 00:00-06:00
- Per-persona response times: INSTANT (5-60s), MINUTES (1-10min), HOURS (30min-4hr), DAYS (12hr-2days)
- Natural gaps between sessions (hours to days)

**Capabilities:**
- Generate conversations with realistic timing patterns
- Progress callbacks for TUI integration
- Exponential backoff retry on LLM failures
- Direct database writing via `generate_to_database()`
- Seed/theme parsing for conversation topics
- Natural topic shift detection during generation

**Example Usage:**
```python
from imessage_data_foundry.conversations import ConversationGenerator
from imessage_data_foundry.llm import ProviderManager

async def generate():
    manager = ProviderManager()
    generator = ConversationGenerator(manager)

    result = await generator.generate(
        personas=[alice, bob],
        config=ConversationConfig(
            participants=[alice.id, bob.id],
            message_count_target=100,
            time_range_start=datetime(2024, 1, 1),
            time_range_end=datetime(2024, 1, 7),
        ),
        progress_callback=lambda p: print(f"{p.percent_complete:.0f}%"),
    )

    # Or write directly to database
    result = await generator.generate_to_database(personas, config, builder)
```

---

## 🔲 Phase 6: Attachments

**Goal:** Create placeholder attachments with valid database records.

| Task | File | Description |
|------|------|-------------|
| 6.1 | `attachments/generator.py` | Create stub files, attachment records |
| 6.2 | `attachments/stubs/` | Template placeholder files (PNG, JPG, HEIC) |

**Lower priority:** This is optional functionality.

---

## 🔲 Phase 7: TUI Application

**Goal:** Interactive Textual interface for the full workflow.

| Task | File | Description |
|------|------|-------------|
| 7.1 | `app.py` | Main Textual App class, screen navigation |
| 7.2 | `ui/screens/welcome.py` | Welcome screen, app overview |
| 7.3 | `ui/screens/config.py` | Configuration (macOS version, output path, API keys) |
| 7.4 | `ui/screens/personas.py` | Persona management (create, edit, delete, list) |
| 7.5 | `ui/screens/conversations.py` | Conversation setup (participants, counts, seeds) |
| 7.6 | `ui/screens/generation.py` | Progress display during generation |
| 7.7 | `ui/widgets/` | Reusable widgets (PersonaCard, ChatPreview, Progress) |
| 7.8 | `ui/styles.tcss` | Textual CSS styling |

**Alternative:** Consider a simpler CLI interface first (`cli.py`) to validate core functionality before building the TUI.

---

## 🔲 Phase 8: Testing & Polish

| Task | File | Description |
|------|------|-------------|
| 8.1 | `tests/test_schema.py` | Schema validation tests |
| 8.2 | `tests/test_personas.py` | Persona CRUD tests |
| 8.3 | `tests/test_conversations.py` | Conversation generation tests |
| 8.4 | `tests/test_timestamps.py` | Timestamp distribution tests |
| 8.5 | Integration test | Verify output works with `imessage-exporter` |

---

## Recommended Path Forward

```
✅ Phase 1 (Complete)
    ↓
🔲 Phase 2.1 → 2.2 → 2.4        (Minimal viable database)
    ↓
Quick validation: Generate a test DB, inspect with sqlite3
    ↓
✅ Phase 3 (Complete)
    ↓
✅ Phase 4 (Complete)
    ↓
✅ Phase 5 (Complete)
    ↓
🔲 Phase 6.1 (basic CLI)        (End-to-end validation)
    ↓
🔲 Phase 6.2+ (TUI screens)     (Full TUI application)
    ↓
🔲 Phase 7 (Testing & Polish)
```

---

## Immediate Next Steps (Phase 6)

1. **Implement basic CLI** (`cli.py`) — Simple command-line interface to validate full pipeline
2. **Test with `imessage-exporter`** — Verify generated databases work with external tools
3. **Build TUI screens** — Welcome, config, personas, conversations, generation progress

---

## Open Research Tasks

- [ ] Extract exact schema from a real Sequoia `chat.db` (requires Full Disk Access)
- [ ] Identify schema differences between Sonoma/Sequoia/Tahoe
- [ ] Determine optimal LLM batch sizes for conversation generation
- [ ] Research `attributedBody` blob format (NSAttributedString plist)

## Success Milestones

| Milestone | Criteria | Status |
|-----------|----------|--------|
| M0: Foundation | All utility functions and models working | ✅ |
| M1: Valid DB | Generate a DB that opens in SQLiteFlow without errors | ✅ |
| M2: Schema Match | Generated schema matches real `chat.db` structure | ✅ |
| M3: Manual Messages | Can programmatically insert messages that appear valid | ✅ |
| M4: LLM Messages | Can generate messages via LLM and insert them | ✅ |
| M5: Full Pipeline | End-to-end: personas → conversations → valid DB | ✅ |
| M6: Tool Compat | Output works with `imessage-exporter` | 🔲 |

---

## Test Coverage

| Phase | Test Files | Tests |
|-------|------------|-------|
| Phase 1 | test_apple_time.py, test_phone_numbers.py, test_persona_models.py, test_conversation_models.py | 63 |
| Phase 2 | test_schema_base.py, test_builder.py, test_validators.py, test_version_detect.py | 103 |
| Phase 3 | test_persona_storage.py | 37 |
| Phase 4 | test_llm_config.py, test_llm_models.py, test_llm_prompts.py, test_llm_manager.py | 65 |
| Phase 5 | test_timestamps.py, test_seeding.py, test_generator.py | 67 |
| **Total** | **16 files** | **335 tests** |
