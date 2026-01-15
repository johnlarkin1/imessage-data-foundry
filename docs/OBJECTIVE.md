# OBJECTIVE.md — iMessage Data Foundry

## Project Vision

**iMessage Data Foundry** is a Python-based tool that generates realistic, schema-accurate iMessage SQLite databases for testing, development, and demonstration purposes. It creates synthetic conversations between AI-generated personas, producing databases that exactly mirror the macOS `chat.db` structure.

## Primary Use Cases

1. **Testing** — Validate iMessage analysis tools, exporters, or forensic applications against realistic data
2. **Development** — Build and test applications that interface with iMessage databases without using real personal data
3. **Demos** — Create convincing demonstration databases for presentations or documentation

## Core Requirements

### Database Generation

| Requirement           | Details                                                         |
| --------------------- | --------------------------------------------------------------- |
| **Schema Fidelity**   | Exact replication of macOS iMessage `chat.db` schema            |
| **macOS Versions**    | Support for Sonoma (14.x), Sequoia (15.x), and Tahoe (26.x)     |
| **Version Selection** | User-selectable with auto-detection of current macOS as default |
| **Table Coverage**    | Full schema replication (~20+ tables including all join tables) |
| **Output Location**   | User-specified custom local path                                |

### Persona System

| Requirement            | Details                                                                                                                                                                                               |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Persona Attributes** | Name, phone number/email, personality description, writing style, relationship to user, communication frequency, typical response time, emoji usage preferences, vocabulary level, topics of interest |
| **Persona Count**      | Up to 20 personas per database                                                                                                                                                                        |
| **Persistence**        | Personas saved in local SQLite database for reuse across generations                                                                                                                                  |
| **Creation Modes**     | Manual definition OR LLM-generated with user approval                                                                                                                                                 |
| **Self Identity**      | User can define their own persona or use a default                                                                                                                                                    |

### Conversation Generation

| Requirement        | Details                                                                                                     |
| ------------------ | ----------------------------------------------------------------------------------------------------------- |
| **Chat Types**     | 1:1 direct messages and group chats                                                                         |
| **Message Volume** | Up to 10,000 messages per contact                                                                           |
| **Timestamps**     | Realistic distribution with natural batching patterns                                                       |
| **Seeding**        | Optional conversation seeds (e.g., "planning a surprise party") or free-form based on persona relationships |
| **LLM Providers**  | Support for OpenAI API and Anthropic API                                                                    |

### Attachments

| Requirement          | Details                                                                      |
| -------------------- | ---------------------------------------------------------------------------- |
| **Support Level**    | Stub/placeholder files                                                       |
| **Types**            | Fake images (placeholder PNGs), placeholder files for other attachment types |
| **Database Records** | Proper `attachment` table entries with realistic metadata                    |

### Features Explicitly NOT Required

- Reactions/tapbacks
- Read receipts & delivery status simulation
- Edited/unsent messages
- Reply threads
- Message effects (bubble/screen effects)

## Technical Stack

| Component           | Technology                          |
| ------------------- | ----------------------------------- |
| **Language**        | Python 3.11+                        |
| **Package Manager** | uv / uvx                            |
| **User Interface**  | Textual (TUI) with Rich for styling |
| **Database**        | SQLite3                             |
| **LLM Integration** | OpenAI SDK, Anthropic SDK           |

## User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    iMessage Data Foundry                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. CONFIGURATION                                               │
│     ├── Select macOS version (auto-detect default)              │
│     ├── Set output database path                                │
│     └── Configure LLM API key (OpenAI or Anthropic)             │
│                                                                 │
│  2. PERSONA MANAGEMENT                                          │
│     ├── Create new personas (manual or LLM-generated)           │
│     ├── Load existing personas from library                     │
│     ├── Edit/delete personas                                    │
│     └── Define "self" persona                                   │
│                                                                 │
│  3. CONVERSATION SETUP                                          │
│     ├── Select personas for conversations                       │
│     ├── Create 1:1 or group chat configurations                 │
│     ├── Set message count targets                               │
│     ├── Optionally provide conversation seeds                   │
│     └── Configure time range for messages                       │
│                                                                 │
│  4. GENERATION                                                  │
│     ├── Generate conversations via LLM                          │
│     ├── Create placeholder attachments                          │
│     ├── Build SQLite database with proper schema                │
│     └── Validate relational integrity                           │
│                                                                 │
│  5. OUTPUT                                                      │
│     └── Save chat.db to specified path                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Success Criteria

1. **Schema Accuracy** — Generated `chat.db` files pass validation against real iMessage database schemas
2. **Tool Compatibility** — Output databases work with existing iMessage analysis tools (e.g., `imessage-exporter`, `imessage_reader`)
3. **Realistic Content** — Generated conversations feel natural and reflect persona personalities
4. **Performance** — Can generate 10k messages in reasonable time (<5 minutes)
5. **Usability** — Intuitive TUI that guides users through the process

## Non-Goals

- Interfacing with real iMessage/Messages.app
- Sending actual messages
- Reading from real `chat.db` files
- Cross-platform support (macOS-focused, though may run on Linux)
- Production-grade security (this is a dev/test tool)

## Open Questions for Implementation

1. How do schema differences between Sonoma/Sequoia/Tahoe manifest? Need to reverse-engineer or document.
2. What's the optimal batch size for LLM conversation generation?
3. Should we support conversation "continuation" (adding more messages to existing chats)?# OBJECTIVE.md — iMessage Data Foundry

## Project Vision

**iMessage Data Foundry** is a Python-based tool that generates realistic, schema-accurate iMessage SQLite databases for testing, development, and demonstration purposes. It creates synthetic conversations between AI-generated personas, producing databases that exactly mirror the macOS `chat.db` structure.

## Primary Use Cases

1. **Testing** — Validate iMessage analysis tools, exporters, or forensic applications against realistic data
2. **Development** — Build and test applications that interface with iMessage databases without using real personal data
3. **Demos** — Create convincing demonstration databases for presentations or documentation

## Core Requirements

### Database Generation

| Requirement           | Details                                                         |
| --------------------- | --------------------------------------------------------------- |
| **Schema Fidelity**   | Exact replication of macOS iMessage `chat.db` schema            |
| **macOS Versions**    | Support for Sonoma (14.x), Sequoia (15.x), and Tahoe (26.x)     |
| **Version Selection** | User-selectable with auto-detection of current macOS as default |
| **Table Coverage**    | Full schema replication (~20+ tables including all join tables) |
| **Output Location**   | User-specified custom local path                                |

### Persona System

| Requirement            | Details                                                                                                                                                                                               |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Persona Attributes** | Name, phone number/email, personality description, writing style, relationship to user, communication frequency, typical response time, emoji usage preferences, vocabulary level, topics of interest |
| **Persona Count**      | Up to 20 personas per database                                                                                                                                                                        |
| **Persistence**        | Personas saved in local SQLite database for reuse across generations                                                                                                                                  |
| **Creation Modes**     | Manual definition OR LLM-generated with user approval                                                                                                                                                 |
| **Self Identity**      | User can define their own persona or use a default                                                                                                                                                    |

### Conversation Generation

| Requirement        | Details                                                                                                     |
| ------------------ | ----------------------------------------------------------------------------------------------------------- |
| **Chat Types**     | 1:1 direct messages and group chats                                                                         |
| **Message Volume** | Up to 10,000 messages per contact                                                                           |
| **Timestamps**     | Realistic distribution with natural batching patterns                                                       |
| **Seeding**        | Optional conversation seeds (e.g., "planning a surprise party") or free-form based on persona relationships |
| **LLM Providers**  | Support for OpenAI API and Anthropic API                                                                    |

### Attachments

| Requirement          | Details                                                                      |
| -------------------- | ---------------------------------------------------------------------------- |
| **Support Level**    | Stub/placeholder files                                                       |
| **Types**            | Fake images (placeholder PNGs), placeholder files for other attachment types |
| **Database Records** | Proper `attachment` table entries with realistic metadata                    |

### Features Explicitly NOT Required

- Reactions/tapbacks
- Read receipts & delivery status simulation
- Edited/unsent messages
- Reply threads
- Message effects (bubble/screen effects)

## Technical Stack

| Component           | Technology                          |
| ------------------- | ----------------------------------- |
| **Language**        | Python 3.11+                        |
| **Package Manager** | uv / uvx                            |
| **User Interface**  | Textual (TUI) with Rich for styling |
| **Database**        | SQLite3                             |
| **LLM Integration** | OpenAI SDK, Anthropic SDK           |

## User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    iMessage Data Foundry                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. CONFIGURATION                                               │
│     ├── Select macOS version (auto-detect default)              │
│     ├── Set output database path                                │
│     └── Configure LLM API key (OpenAI or Anthropic)             │
│                                                                 │
│  2. PERSONA MANAGEMENT                                          │
│     ├── Create new personas (manual or LLM-generated)           │
│     ├── Load existing personas from library                     │
│     ├── Edit/delete personas                                    │
│     └── Define "self" persona                                   │
│                                                                 │
│  3. CONVERSATION SETUP                                          │
│     ├── Select personas for conversations                       │
│     ├── Create 1:1 or group chat configurations                 │
│     ├── Set message count targets                               │
│     ├── Optionally provide conversation seeds                   │
│     └── Configure time range for messages                       │
│                                                                 │
│  4. GENERATION                                                  │
│     ├── Generate conversations via LLM                          │
│     ├── Create placeholder attachments                          │
│     ├── Build SQLite database with proper schema                │
│     └── Validate relational integrity                           │
│                                                                 │
│  5. OUTPUT                                                      │
│     └── Save chat.db to specified path                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Success Criteria

1. **Schema Accuracy** — Generated `chat.db` files pass validation against real iMessage database schemas
2. **Tool Compatibility** — Output databases work with existing iMessage analysis tools (e.g., `imessage-exporter`, `imessage_reader`)
3. **Realistic Content** — Generated conversations feel natural and reflect persona personalities
4. **Performance** — Can generate 10k messages in reasonable time (<5 minutes)
5. **Usability** — Intuitive TUI that guides users through the process

## Non-Goals

- Interfacing with real iMessage/Messages.app
- Sending actual messages
- Reading from real `chat.db` files
- Cross-platform support (macOS-focused, though may run on Linux)
- Production-grade security (this is a dev/test tool)

## Open Questions for Implementation

1. How do schema differences between Sonoma/Sequoia/Tahoe manifest? Need to reverse-engineer or document.
2. What's the optimal batch size for LLM conversation generation?
3. Should we support conversation "continuation" (adding more messages to existing chats)?
