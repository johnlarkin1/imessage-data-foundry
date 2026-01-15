# ROADMAP.md — Implementation Plan

## Current State

- ✅ Project scaffolding (pyproject.toml, basic entry points)
- ✅ Documentation (OBJECTIVE.md, ARCHITECTURE.md, SCHEMA_NOTES.md, CLAUDE.md)
- ✅ **Phase 1: Foundation & Utilities** — Complete
- 🔲 Phase 2: Database Layer — **Up Next**
- 🔲 Phase 3-8: Remaining functionality

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

## 🔲 Phase 3: Persona System

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

**Note:** Implement Anthropic first (we're already using Claude).

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
🔲 Phase 3.1 → 3.2              (Persona storage without LLM)
    ↓
🔲 Phase 4.1 → 4.2 → 4.3        (LLM integration)
    ↓
🔲 Phase 5.1 → 5.2              (Core conversation generation)
    ↓
🔲 Phase 7.1 (basic CLI)        (End-to-end test)
    ↓
Remaining phases as needed
```

---

## Immediate Next Steps (Phase 2)

1. **Research the actual Sequoia schema** — Extract from real `chat.db` (requires Full Disk Access)
2. **Implement `db/schema/base.py`** — Define common table structures
3. **Implement `db/schema/sequoia.py`** — Complete schema as SQL strings
4. **Implement `db/builder.py`** — The core DatabaseBuilder class

## Open Research Tasks

- [ ] Extract exact schema from a real Sequoia `chat.db` (requires Full Disk Access)
- [ ] Identify schema differences between Sonoma/Sequoia/Tahoe
- [ ] Determine optimal LLM batch sizes for conversation generation
- [ ] Research `attributedBody` blob format (NSAttributedString plist)

## Success Milestones

| Milestone | Criteria | Status |
|-----------|----------|--------|
| M0: Foundation | All utility functions and models working | ✅ |
| M1: Valid DB | Generate a DB that opens in SQLiteFlow without errors | 🔲 |
| M2: Schema Match | Generated schema matches real `chat.db` structure | 🔲 |
| M3: Manual Messages | Can programmatically insert messages that appear valid | 🔲 |
| M4: LLM Messages | Can generate messages via LLM and insert them | 🔲 |
| M5: Full Pipeline | End-to-end: personas → conversations → valid DB | 🔲 |
| M6: Tool Compat | Output works with `imessage-exporter` | 🔲 |
