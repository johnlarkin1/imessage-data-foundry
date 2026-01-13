# ROADMAP.md — Implementation Plan

## Current State

- ✅ Project scaffolding (pyproject.toml, basic entry points)
- ✅ Documentation (OBJECTIVE.md, ARCHITECTURE.md, SCHEMA_NOTES.md, CLAUDE.md)
- ✅ **Phase 1: Foundation & Utilities** — Complete
- ✅ **Phase 2: Database Layer** — Complete
- 🔲 Phase 3: Persona System — **Up Next**
- 🔲 Phase 4-7: Remaining functionality

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
- 647 lines of tests across 4 test files
- Makefile with lint/fmt/test/run targets

---

## ✅ Phase 2: Database Layer (COMPLETE)

**Goal:** Generate valid `chat.db` files that pass schema validation.

| Task | File | Status | Description |
|------|------|--------|-------------|
| 2.1 | `db/schema/base.py` | ✅ | Common schema elements, 11 table generators, GUID helpers |
| 2.2 | `db/schema/sequoia.py` | ✅ | macOS 15 Sequoia schema (100+ column message table) |
| 2.3 | `db/version_detect.py` | ✅ | Auto-detect macOS version, schema version mapping |
| 2.4 | `db/builder.py` | ✅ | DatabaseBuilder class with full CRUD operations |
| 2.5 | `db/validators.py` | ✅ | Schema validation, FK integrity, GUID uniqueness |
| 2.6 | `db/schema/sonoma.py` | ✅ | macOS 14 Sonoma schema |
| 2.7 | `db/schema/tahoe.py` | ✅ | macOS 26 Tahoe schema (placeholder, inherits Sequoia) |

**Deliverables:**
- `DatabaseBuilder` class (557 lines) - handles, chats, messages, attachments, batch ops
- Schema validation suite (402 lines) - 6 validation functions
- Version detection (111 lines) - auto-detect macOS version
- Three schema versions: Sonoma, Sequoia, Tahoe
- 727 lines of tests across 4 test files
- Context manager support for clean resource handling

**Capabilities:**
- Create SQLite databases from scratch
- Add handles (contacts) with deduplication
- Create direct/group chats with proper GUIDs
- Insert messages with automatic GUID generation
- Batch message insertion for performance
- Attachment management with join tables
- Full schema validation against reference databases

**Example Usage:**
```python
from imessage_data_foundry.db.builder import DatabaseBuilder

with DatabaseBuilder("chat.db", version="sequoia") as builder:
    h1 = builder.add_handle("+15551234567")
    h2 = builder.add_handle("+15559876543")
    chat = builder.create_chat([h1, h2], chat_type="direct")
    builder.add_message(chat, h1, "Hello!", is_from_me=False, date=1000000000)
    builder.add_message(chat, None, "Hi there!", is_from_me=True, date=1000060000)
```

---

## 🔲 Phase 3: Persona System (UP NEXT)

**Goal:** Create, store, and manage personas for conversation generation.

| Task | File | Description |
|------|------|-------------|
| 3.1 | `personas/storage.py` | SQLite persistence for personas (foundry.db) |
| 3.2 | `personas/library.py` | CRUD operations, import/export |
| 3.3 | `personas/generator.py` | LLM-based persona generation (requires Phase 4) |

**Dependency:** Task 3.3 requires Phase 4 LLM integration.

---

## 🔲 Phase 4: LLM Integration

**Goal:** Abstract interface for persona and message generation.

| Task | File | Description |
|------|------|-------------|
| 4.1 | `llm/base.py` | Abstract LLMProvider interface |
| 4.2 | `llm/prompts.py` | Prompt templates for persona/conversation generation |
| 4.3 | `llm/anthropic_provider.py` | Anthropic Claude implementation |
| 4.4 | `llm/openai_provider.py` | OpenAI GPT implementation |

**Note:** Implement Anthropic first (we're already using Claude). Dependencies already installed.

---

## 🔲 Phase 5: Conversation Generation

**Goal:** Generate realistic message threads with proper timestamps.

| Task | File | Description |
|------|------|-------------|
| 5.1 | `conversations/timestamps.py` | Realistic timestamp distribution algorithm |
| 5.2 | `conversations/generator.py` | Orchestrates LLM calls, batch generation |
| 5.3 | `conversations/seeding.py` | Conversation themes/seeds handling |

**Key algorithm:** Timestamp generation needs:
- Conversation sessions (clusters of 5-30 rapid messages)
- Natural gaps between sessions (hours to days)
- Circadian weighting (fewer messages at 3am)
- Per-persona response time variation

---

## 🔲 Phase 6: TUI Application

**Goal:** Interactive Textual interface for the full workflow.

| Task | File | Description |
|------|------|-------------|
| 6.1 | `app.py` | Main Textual App class, screen navigation |
| 6.2 | `ui/screens/welcome.py` | Welcome screen, app overview |
| 6.3 | `ui/screens/config.py` | Configuration (macOS version, output path, API keys) |
| 6.4 | `ui/screens/personas.py` | Persona management (create, edit, delete, list) |
| 6.5 | `ui/screens/conversations.py` | Conversation setup (participants, counts, seeds) |
| 6.6 | `ui/screens/generation.py` | Progress display during generation |
| 6.7 | `ui/widgets/` | Reusable widgets (PersonaCard, ChatPreview, Progress) |
| 6.8 | `ui/styles.tcss` | Textual CSS styling |

**Alternative:** Consider a simpler CLI interface first (`cli.py`) to validate core functionality before building the TUI.

---

## 🔲 Phase 7: Testing & Polish

| Task | File | Description |
|------|------|-------------|
| 7.1 | Integration test | Verify output works with `imessage-exporter` |
| 7.2 | End-to-end tests | Full pipeline testing |
| 7.3 | Performance tests | Batch insert benchmarks |

---

## Recommended Path Forward

```
✅ Phase 1 (Complete)
    ↓
✅ Phase 2 (Complete)
    ↓
🔲 Phase 3.1 → 3.2              (Persona storage without LLM)
    ↓
🔲 Phase 4.1 → 4.2 → 4.3        (LLM integration)
    ↓
🔲 Phase 5.1 → 5.2              (Core conversation generation)
    ↓
🔲 Phase 6.1 (basic CLI)        (End-to-end test)
    ↓
Remaining phases as needed
```

---

## Immediate Next Steps (Phase 3)

1. **Implement `personas/storage.py`** — SQLite persistence for personas in `foundry.db`
2. **Implement `personas/library.py`** — CRUD operations (add, edit, delete, list)
3. **Add persona import/export** — JSON format for sharing persona sets

---

## Open Research Tasks

- [x] Extract exact schema from a real Sequoia `chat.db`
- [x] Identify schema differences between Sonoma/Sequoia
- [ ] Determine optimal LLM batch sizes for conversation generation
- [ ] Research `attributedBody` blob format (NSAttributedString plist)
- [ ] Test generated databases with `imessage-exporter`

---

## Success Milestones

| Milestone | Criteria | Status |
|-----------|----------|--------|
| M0: Foundation | All utility functions and models working | ✅ |
| M1: Valid DB | Generate a DB that opens in SQLiteFlow without errors | ✅ |
| M2: Schema Match | Generated schema matches real `chat.db` structure | ✅ |
| M3: Manual Messages | Can programmatically insert messages that appear valid | ✅ |
| M4: LLM Messages | Can generate messages via LLM and insert them | 🔲 |
| M5: Full Pipeline | End-to-end: personas → conversations → valid DB | 🔲 |
| M6: Tool Compat | Output works with `imessage-exporter` | 🔲 |

---

## Test Coverage

| Phase | Test Files | Lines |
|-------|------------|-------|
| Phase 1 | test_apple_time.py, test_phone_numbers.py, test_persona_models.py, test_conversation_models.py | 647 |
| Phase 2 | test_schema_base.py, test_builder.py, test_validators.py, test_version_detect.py | 727 |
| **Total** | 8 files | **1,374** |
