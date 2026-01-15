"""Tests for conversation generator."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from imessage_data_foundry.conversations.generator import (
    ConversationGenerator,
    GenerationProgress,
    LLMGenerationError,
    TimestampedMessage,
    ValidationError,
    validate_generation_inputs,
)
from imessage_data_foundry.llm.config import LLMConfig
from imessage_data_foundry.llm.models import GeneratedMessage
from imessage_data_foundry.personas.models import (
    ChatType,
    ConversationConfig,
    Persona,
)


def make_persona(
    name: str = "Test",
    identifier: str = "+15551234567",
    is_self: bool = False,
    persona_id: str | None = None,
) -> Persona:
    persona = Persona(
        name=name,
        identifier=identifier,
        is_self=is_self,
    )
    if persona_id:
        persona.id = persona_id
    return persona


def make_config(
    participants: list[str],
    message_count: int = 10,
    chat_type: ChatType = ChatType.DIRECT,
) -> ConversationConfig:
    return ConversationConfig(
        participants=participants,
        message_count_target=message_count,
        time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
        time_range_end=datetime(2024, 1, 7, tzinfo=UTC),
        chat_type=chat_type,
    )


class MockLLMProvider:
    def __init__(self, persona_ids: list[str]):
        self.persona_ids = persona_ids
        self._call_count = 0
        self.name = "Mock"

    async def generate_messages(
        self,
        persona_descriptions: list[dict[str, str]],
        context: list[GeneratedMessage],
        count: int,
        seed: str | None = None,  # noqa: ARG002
    ) -> list[GeneratedMessage]:
        self._call_count += 1

        messages = []
        for i in range(count):
            sender_idx = (len(context) + i) % len(self.persona_ids)
            sender_id = self.persona_ids[sender_idx]
            is_self = any(
                p.get("is_self") == "True" and p["id"] == sender_id for p in persona_descriptions
            )

            messages.append(
                GeneratedMessage(
                    text=f"Test message {self._call_count}-{i}",
                    sender_id=sender_id,
                    is_from_me=is_self,
                )
            )

        return messages


class TestValidateGenerationInputs:
    def test_valid_inputs(self):
        alice = make_persona("Alice", "+15551111111", is_self=True, persona_id="alice")
        bob = make_persona("Bob", "+15552222222", persona_id="bob")
        config = make_config(participants=["alice", "bob"])

        errors = validate_generation_inputs([alice, bob], config)

        assert errors == []

    def test_missing_participant(self):
        alice = make_persona("Alice", "+15551111111", is_self=True, persona_id="alice")
        config = make_config(participants=["alice", "bob"])

        errors = validate_generation_inputs([alice], config)

        assert any("bob" in e for e in errors)

    def test_no_self_persona(self):
        alice = make_persona("Alice", "+15551111111", persona_id="alice")
        bob = make_persona("Bob", "+15552222222", persona_id="bob")
        config = make_config(participants=["alice", "bob"])

        errors = validate_generation_inputs([alice, bob], config)

        assert any("is_self" in e for e in errors)

    def test_multiple_self_personas(self):
        alice = make_persona("Alice", "+15551111111", is_self=True, persona_id="alice")
        bob = make_persona("Bob", "+15552222222", is_self=True, persona_id="bob")
        config = make_config(participants=["alice", "bob"])

        errors = validate_generation_inputs([alice, bob], config)

        assert any("Multiple" in e for e in errors)


class TestGenerationProgress:
    def test_percent_complete(self):
        progress = GenerationProgress(
            total_messages=100,
            generated_messages=50,
            current_batch=2,
            total_batches=4,
            phase="generating",
        )

        assert progress.percent_complete == 50.0

    def test_percent_complete_zero_total(self):
        progress = GenerationProgress(
            total_messages=0,
            generated_messages=0,
            current_batch=0,
            total_batches=0,
            phase="generating",
        )

        assert progress.percent_complete == 100.0


class TestConversationGenerator:
    @pytest.fixture
    def sample_personas(self):
        alice = make_persona("Alice", "+15551111111", is_self=True, persona_id="alice")
        bob = make_persona("Bob", "+15552222222", persona_id="bob")
        return [alice, bob]

    @pytest.fixture
    def mock_provider_manager(self, sample_personas):
        manager = MagicMock()
        provider = MockLLMProvider([p.id for p in sample_personas])
        manager.get_provider = AsyncMock(return_value=provider)
        return manager

    @pytest.fixture
    def generator(self, mock_provider_manager):
        config = LLMConfig()
        config.message_batch_size = 5
        config.context_window_size = 3
        return ConversationGenerator(mock_provider_manager, config)

    @pytest.mark.asyncio
    async def test_generates_correct_count(self, generator, sample_personas):
        config = make_config(
            participants=[p.id for p in sample_personas],
            message_count=10,
        )

        result = await generator.generate(sample_personas, config)

        assert len(result.messages) == 10

    @pytest.mark.asyncio
    async def test_assigns_timestamps(self, generator, sample_personas):
        config = make_config(
            participants=[p.id for p in sample_personas],
            message_count=10,
        )

        result = await generator.generate(sample_personas, config)

        for tm in result.messages:
            assert isinstance(tm, TimestampedMessage)
            assert tm.timestamp > 0

    @pytest.mark.asyncio
    async def test_validates_inputs(self, generator, sample_personas):
        config = make_config(participants=["alice", "unknown"])

        with pytest.raises(ValidationError, match="unknown"):
            await generator.generate(sample_personas, config)

    @pytest.mark.asyncio
    async def test_progress_callback_called(self, generator, sample_personas):
        config = make_config(
            participants=[p.id for p in sample_personas],
            message_count=10,
        )
        progress_updates: list[GenerationProgress] = []

        await generator.generate(
            sample_personas,
            config,
            progress_callback=lambda p: progress_updates.append(p),
        )

        assert len(progress_updates) > 0
        phases = {p.phase for p in progress_updates}
        assert "generating" in phases

    @pytest.mark.asyncio
    async def test_returns_provider_name(self, generator, sample_personas):
        config = make_config(
            participants=[p.id for p in sample_personas],
            message_count=10,
        )

        result = await generator.generate(sample_personas, config)

        assert result.llm_provider_used == "Mock"

    @pytest.mark.asyncio
    async def test_returns_generation_time(self, generator, sample_personas):
        config = make_config(
            participants=[p.id for p in sample_personas],
            message_count=10,
        )

        result = await generator.generate(sample_personas, config)

        assert result.generation_time_seconds > 0


class TestFormatPersonasForLLM:
    def test_includes_required_fields(self):
        manager = MagicMock()
        generator = ConversationGenerator(manager)

        persona = make_persona("Alice", "+15551111111", is_self=True)
        persona.personality = "Friendly"
        persona.writing_style = "casual"
        persona.topics_of_interest = ["music", "travel"]

        result = generator._format_personas_for_llm([persona])

        assert len(result) == 1
        desc = result[0]
        assert desc["id"] == persona.id
        assert desc["name"] == "Alice"
        assert desc["personality"] == "Friendly"
        assert desc["writing_style"] == "casual"
        assert desc["is_self"] == "True"
        assert "music" in desc["topics"]

    def test_is_self_marker(self):
        manager = MagicMock()
        generator = ConversationGenerator(manager)

        alice = make_persona("Alice", is_self=True)
        bob = make_persona("Bob", is_self=False)

        result = generator._format_personas_for_llm([alice, bob])

        alice_desc = next(d for d in result if d["name"] == "Alice")
        bob_desc = next(d for d in result if d["name"] == "Bob")

        assert alice_desc["is_self"] == "True"
        assert bob_desc["is_self"] == "False"


class TestPrepareMessagesForDB:
    def test_outgoing_message_no_handle(self):
        manager = MagicMock()
        generator = ConversationGenerator(manager)

        msg = GeneratedMessage(text="Hello", sender_id="alice", is_from_me=True)
        tm = TimestampedMessage(message=msg, timestamp=1000000)

        handle_map = {"bob": 1}

        result = generator._prepare_messages_for_db([tm], handle_map)

        assert len(result) == 1
        handle_id, text, is_from_me, timestamp = result[0]
        assert handle_id is None
        assert text == "Hello"
        assert is_from_me is True
        assert timestamp == 1000000

    def test_incoming_message_has_handle(self):
        manager = MagicMock()
        generator = ConversationGenerator(manager)

        msg = GeneratedMessage(text="Hi there", sender_id="bob", is_from_me=False)
        tm = TimestampedMessage(message=msg, timestamp=2000000)

        handle_map = {"bob": 42}

        result = generator._prepare_messages_for_db([tm], handle_map)

        assert len(result) == 1
        handle_id, text, is_from_me, timestamp = result[0]
        assert handle_id == 42
        assert text == "Hi there"
        assert is_from_me is False


class TestLLMGenerationError:
    def test_stores_partial_messages(self):
        partial = [GeneratedMessage(text="partial", sender_id="a", is_from_me=True)]
        error = LLMGenerationError("Failed", partial_messages=partial)

        assert error.partial_messages == partial
        assert str(error) == "Failed"

    def test_default_empty_partial(self):
        error = LLMGenerationError("Failed")

        assert error.partial_messages == []


class TestBatchRetry:
    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        manager = MagicMock()
        config = LLMConfig()
        config.message_batch_size = 5
        generator = ConversationGenerator(manager, config)

        call_count = 0

        async def failing_then_success(
            *_args,
            **kwargs,  # noqa: ARG001
        ):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Temporary failure")
            return [
                GeneratedMessage(text="Success", sender_id="a", is_from_me=True)
                for _ in range(kwargs.get("count", 1))
            ]

        provider = MagicMock()
        provider.generate_messages = failing_then_success

        result = await generator._generate_batch_with_retry(
            provider=provider,
            persona_descriptions=[],
            context=[],
            count=1,
            seed=None,
            max_retries=3,
        )

        assert len(result) == 1
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        manager = MagicMock()
        generator = ConversationGenerator(manager)

        async def always_fail(
            *_args,
            **_kwargs,  # noqa: ARG001
        ):
            raise RuntimeError("Always fails")

        provider = MagicMock()
        provider.generate_messages = always_fail

        with pytest.raises(LLMGenerationError, match="Failed after 3 attempts"):
            await generator._generate_batch_with_retry(
                provider=provider,
                persona_descriptions=[],
                context=[],
                count=1,
                seed=None,
                max_retries=3,
            )
