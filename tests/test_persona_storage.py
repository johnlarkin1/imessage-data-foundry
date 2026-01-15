import json
import sqlite3
import time
from pathlib import Path

import pytest

from imessage_data_foundry.personas.models import (
    CommunicationFrequency,
    EmojiUsage,
    IdentifierType,
    Persona,
    ResponseTime,
    VocabularyLevel,
)
from imessage_data_foundry.personas.storage import (
    PersonaNotFoundError,
    PersonaStorage,
    get_default_db_path,
)


@pytest.fixture
def storage(tmp_path: Path) -> PersonaStorage:
    db_path = tmp_path / "test_foundry.db"
    s = PersonaStorage(db_path)
    yield s
    s.close()


@pytest.fixture
def sample_persona() -> Persona:
    return Persona(
        name="Test User",
        identifier="+15551234567",
        identifier_type=IdentifierType.PHONE,
        personality="Friendly and outgoing",
        writing_style="casual",
        relationship="friend",
        communication_frequency=CommunicationFrequency.MEDIUM,
        typical_response_time=ResponseTime.MINUTES,
        emoji_usage=EmojiUsage.LIGHT,
        vocabulary_level=VocabularyLevel.MODERATE,
        topics_of_interest=["movies", "hiking"],
    )


class TestPersonaStorageInit:
    def test_creates_database_file(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        storage = PersonaStorage(db_path)
        _ = storage.connection
        assert db_path.exists()
        storage.close()

    def test_creates_parent_directories(self, tmp_path: Path):
        db_path = tmp_path / "subdir" / "nested" / "test.db"
        storage = PersonaStorage(db_path)
        _ = storage.connection
        assert db_path.exists()
        storage.close()

    def test_context_manager(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with PersonaStorage(db_path) as storage:
            assert storage.count() == 0

    def test_creates_tables(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with PersonaStorage(db_path) as storage:
            tables = storage.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t["name"] for t in tables]
            assert "personas" in table_names
            assert "generation_history" in table_names

    def test_creates_indexes(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        with PersonaStorage(db_path) as storage:
            indexes = storage.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            index_names = [i["name"] for i in indexes]
            assert "idx_personas_name" in index_names
            assert "idx_personas_is_self" in index_names
            assert "idx_personas_identifier" in index_names


class TestGetDefaultDbPath:
    def test_returns_path(self):
        path = get_default_db_path()
        assert isinstance(path, Path)
        assert path.name == "foundry.db"

    def test_respects_env_var(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        config_path = tmp_path / "config" / "settings.toml"
        monkeypatch.setenv("IMESSAGE_FOUNDRY_CONFIG", str(config_path))
        path = get_default_db_path()
        assert path == tmp_path / "config" / "foundry.db"


class TestCreate:
    def test_creates_persona(self, storage: PersonaStorage, sample_persona: Persona):
        result = storage.create(sample_persona)
        assert result.id == sample_persona.id
        assert storage.count() == 1

    def test_persists_all_fields(self, storage: PersonaStorage, sample_persona: Persona):
        storage.create(sample_persona)
        retrieved = storage.get(sample_persona.id)
        assert retrieved.name == sample_persona.name
        assert retrieved.identifier == sample_persona.identifier
        assert retrieved.personality == sample_persona.personality
        assert retrieved.topics_of_interest == sample_persona.topics_of_interest
        assert retrieved.is_self == sample_persona.is_self

    def test_duplicate_id_raises(self, storage: PersonaStorage, sample_persona: Persona):
        storage.create(sample_persona)
        with pytest.raises(sqlite3.IntegrityError):
            storage.create(sample_persona)


class TestGet:
    def test_returns_persona(self, storage: PersonaStorage, sample_persona: Persona):
        storage.create(sample_persona)
        result = storage.get(sample_persona.id)
        assert result.name == sample_persona.name

    def test_not_found_raises(self, storage: PersonaStorage):
        with pytest.raises(PersonaNotFoundError):
            storage.get("nonexistent-id")


class TestGetByName:
    def test_finds_by_exact_name(self, storage: PersonaStorage):
        p1 = Persona(name="Alice", identifier="+15551111111")
        p2 = Persona(name="Bob", identifier="+15552222222")
        storage.create(p1)
        storage.create(p2)
        results = storage.get_by_name("Alice")
        assert len(results) == 1
        assert results[0].name == "Alice"

    def test_finds_by_partial_name(self, storage: PersonaStorage):
        p1 = Persona(name="Alice Smith", identifier="+15551111111")
        p2 = Persona(name="Alice Jones", identifier="+15552222222")
        p3 = Persona(name="Bob", identifier="+15553333333")
        storage.create_many([p1, p2, p3])
        results = storage.get_by_name("Alice")
        assert len(results) == 2

    def test_case_insensitive(self, storage: PersonaStorage):
        p = Persona(name="Alice", identifier="+15551111111")
        storage.create(p)
        results = storage.get_by_name("alice")
        assert len(results) == 1

    def test_returns_empty_for_no_match(self, storage: PersonaStorage):
        p = Persona(name="Alice", identifier="+15551111111")
        storage.create(p)
        results = storage.get_by_name("Zzzz")
        assert len(results) == 0


class TestGetSelf:
    def test_returns_self_persona(self, storage: PersonaStorage):
        me = Persona(name="Me", identifier="+15551234567", is_self=True)
        other = Persona(name="Other", identifier="+15559876543", is_self=False)
        storage.create(me)
        storage.create(other)
        result = storage.get_self()
        assert result is not None
        assert result.is_self is True
        assert result.name == "Me"

    def test_returns_none_if_no_self(self, storage: PersonaStorage):
        p = Persona(name="Other", identifier="+15551234567", is_self=False)
        storage.create(p)
        assert storage.get_self() is None


class TestUpdate:
    def test_updates_persona(self, storage: PersonaStorage, sample_persona: Persona):
        storage.create(sample_persona)
        sample_persona.name = "Updated Name"
        sample_persona.personality = "Now more serious"
        storage.update(sample_persona)
        retrieved = storage.get(sample_persona.id)
        assert retrieved.name == "Updated Name"
        assert retrieved.personality == "Now more serious"

    def test_updates_updated_at(self, storage: PersonaStorage, sample_persona: Persona):
        storage.create(sample_persona)
        original_updated_at = sample_persona.updated_at
        time.sleep(0.01)
        storage.update(sample_persona)
        retrieved = storage.get(sample_persona.id)
        assert retrieved.updated_at > original_updated_at

    def test_not_found_raises(self, storage: PersonaStorage, sample_persona: Persona):
        with pytest.raises(PersonaNotFoundError):
            storage.update(sample_persona)


class TestDelete:
    def test_deletes_persona(self, storage: PersonaStorage, sample_persona: Persona):
        storage.create(sample_persona)
        assert storage.count() == 1
        storage.delete(sample_persona.id)
        assert storage.count() == 0

    def test_not_found_raises(self, storage: PersonaStorage):
        with pytest.raises(PersonaNotFoundError):
            storage.delete("nonexistent-id")


class TestListAll:
    def test_returns_all_personas(self, storage: PersonaStorage):
        personas = [
            Persona(name="Alice", identifier="+15551111111"),
            Persona(name="Bob", identifier="+15552222222"),
            Persona(name="Charlie", identifier="+15553333333"),
        ]
        storage.create_many(personas)
        results = storage.list_all()
        assert len(results) == 3

    def test_ordered_by_name(self, storage: PersonaStorage):
        personas = [
            Persona(name="Charlie", identifier="+15553333333"),
            Persona(name="Alice", identifier="+15551111111"),
            Persona(name="Bob", identifier="+15552222222"),
        ]
        storage.create_many(personas)
        results = storage.list_all()
        names = [p.name for p in results]
        assert names == ["Alice", "Bob", "Charlie"]

    def test_empty_list(self, storage: PersonaStorage):
        assert storage.list_all() == []


class TestCount:
    def test_returns_count(self, storage: PersonaStorage):
        assert storage.count() == 0
        storage.create(Persona(name="Test", identifier="+15551234567"))
        assert storage.count() == 1


class TestExists:
    def test_returns_true_if_exists(self, storage: PersonaStorage, sample_persona: Persona):
        storage.create(sample_persona)
        assert storage.exists(sample_persona.id) is True

    def test_returns_false_if_not_exists(self, storage: PersonaStorage):
        assert storage.exists("nonexistent") is False


class TestCreateMany:
    def test_creates_multiple(self, storage: PersonaStorage):
        personas = [
            Persona(name="Alice", identifier="+15551111111"),
            Persona(name="Bob", identifier="+15552222222"),
        ]
        result = storage.create_many(personas)
        assert len(result) == 2
        assert storage.count() == 2


class TestDeleteAll:
    def test_deletes_all(self, storage: PersonaStorage):
        personas = [
            Persona(name="Alice", identifier="+15551111111"),
            Persona(name="Bob", identifier="+15552222222"),
        ]
        storage.create_many(personas)
        count = storage.delete_all()
        assert count == 2
        assert storage.count() == 0


class TestExportImport:
    def test_export_all(self, storage: PersonaStorage, sample_persona: Persona):
        storage.create(sample_persona)
        exported = storage.export_all()
        assert len(exported) == 1
        assert exported[0]["name"] == sample_persona.name
        json.dumps(exported)

    def test_import_personas(self, storage: PersonaStorage, sample_persona: Persona):
        data = [sample_persona.model_dump(mode="json")]
        result = storage.import_personas(data)
        assert len(result) == 1
        assert storage.count() == 1

    def test_import_skips_existing(self, storage: PersonaStorage, sample_persona: Persona):
        storage.create(sample_persona)
        data = [sample_persona.model_dump(mode="json")]
        result = storage.import_personas(data, replace=False)
        assert len(result) == 0
        assert storage.count() == 1

    def test_import_replaces_existing(self, storage: PersonaStorage, sample_persona: Persona):
        storage.create(sample_persona)
        sample_persona.name = "Updated Name"
        data = [sample_persona.model_dump(mode="json")]
        storage.import_personas(data, replace=True)
        retrieved = storage.get(sample_persona.id)
        assert retrieved.name == "Updated Name"

    def test_roundtrip(self, storage: PersonaStorage, tmp_path: Path):
        personas = [
            Persona(name="Alice", identifier="+15551111111", topics_of_interest=["a", "b"]),
            Persona(name="Bob", identifier="+15552222222", is_self=True),
        ]
        storage.create_many(personas)
        exported = storage.export_all()

        new_storage = PersonaStorage(tmp_path / "new.db")
        new_storage.import_personas(exported)

        assert new_storage.count() == 2
        alice = new_storage.get_by_name("Alice")[0]
        assert alice.topics_of_interest == ["a", "b"]
        new_storage.close()


class TestEnumSerialization:
    def test_enums_persist_correctly(self, storage: PersonaStorage):
        persona = Persona(
            name="Test",
            identifier="test@example.com",
            identifier_type=IdentifierType.EMAIL,
            communication_frequency=CommunicationFrequency.HIGH,
            typical_response_time=ResponseTime.DAYS,
            emoji_usage=EmojiUsage.HEAVY,
            vocabulary_level=VocabularyLevel.SOPHISTICATED,
        )
        storage.create(persona)

        retrieved = storage.get(persona.id)
        assert retrieved.identifier_type == IdentifierType.EMAIL
        assert retrieved.communication_frequency == CommunicationFrequency.HIGH
        assert retrieved.typical_response_time == ResponseTime.DAYS
        assert retrieved.emoji_usage == EmojiUsage.HEAVY
        assert retrieved.vocabulary_level == VocabularyLevel.SOPHISTICATED
