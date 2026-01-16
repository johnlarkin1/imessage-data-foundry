import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from imessage_data_foundry.conversations.constants import (
    DB_WRITE_CHUNK_SIZE,
    DEFAULT_MAX_RETRIES,
)
from imessage_data_foundry.conversations.timestamps import generate_timestamps
from imessage_data_foundry.db.builder import DatabaseBuilder
from imessage_data_foundry.llm.base import LLMProvider
from imessage_data_foundry.llm.config import LLMConfig
from imessage_data_foundry.llm.manager import ProviderManager
from imessage_data_foundry.llm.models import GeneratedMessage
from imessage_data_foundry.personas.models import ChatType, ConversationConfig, Persona


class GenerationPhase(str, Enum):
    GENERATING = "generating"
    ASSIGNING_TIMESTAMPS = "assigning_timestamps"
    WRITING_DATABASE = "writing_database"


class GenerationError(Exception):
    pass


class LLMGenerationError(GenerationError):
    def __init__(self, message: str, partial_messages: list[GeneratedMessage] | None = None):
        super().__init__(message)
        self.partial_messages = partial_messages or []


class ValidationError(GenerationError):
    pass


@dataclass
class GenerationProgress:
    total_messages: int
    generated_messages: int
    current_batch: int
    total_batches: int
    phase: GenerationPhase

    @property
    def percent_complete(self) -> float:
        if self.total_messages == 0:
            return 100.0
        return (self.generated_messages / self.total_messages) * 100


@dataclass
class TimestampedMessage:
    message: GeneratedMessage
    timestamp: int


@dataclass
class GenerationResult:
    messages: list[TimestampedMessage]
    chat_id: int | None
    handles: dict[str, int]
    generation_time_seconds: float
    llm_provider_used: str


ProgressCallback = Callable[[GenerationProgress], None]


def validate_generation_inputs(
    personas: list[Persona],
    config: ConversationConfig,
) -> list[str]:
    errors: list[str] = []

    persona_ids = {p.id for p in personas}
    for participant_id in config.participants:
        if participant_id not in persona_ids:
            errors.append(f"Participant {participant_id} not found in personas")

    self_personas = [p for p in personas if p.is_self]
    if len(self_personas) == 0:
        errors.append("No persona marked as is_self=True")
    elif len(self_personas) > 1:
        errors.append("Multiple personas marked as is_self=True")

    if config.time_range_end <= config.time_range_start:
        errors.append("time_range_end must be after time_range_start")

    return errors


class ConversationGenerator:
    def __init__(
        self,
        provider_manager: ProviderManager,
        config: LLMConfig | None = None,
    ):
        self.provider_manager = provider_manager
        self.config = config or LLMConfig()
        self._partial_messages: list[GeneratedMessage] = []

    async def generate(
        self,
        personas: list[Persona],
        config: ConversationConfig,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        start_time = time.monotonic()

        errors = validate_generation_inputs(personas, config)
        if errors:
            raise ValidationError("; ".join(errors))

        provider = await self.provider_manager.get_provider()
        persona_descriptions = self._format_personas_for_llm(personas)

        messages = await self._generate_all_messages(
            provider=provider,
            persona_descriptions=persona_descriptions,
            target_count=config.message_count_target,
            seed=config.seed,
            progress_callback=progress_callback,
        )

        if progress_callback:
            progress_callback(
                GenerationProgress(
                    total_messages=config.message_count_target,
                    generated_messages=len(messages),
                    current_batch=0,
                    total_batches=0,
                    phase=GenerationPhase.ASSIGNING_TIMESTAMPS,
                )
            )

        participant_personas = [p for p in personas if p.id in config.participants]
        timestamps = generate_timestamps(
            start=config.time_range_start,
            end=config.time_range_end,
            count=len(messages),
            personas=participant_personas,
        )

        timestamped_messages = [
            TimestampedMessage(message=msg, timestamp=ts)
            for msg, ts in zip(messages, timestamps, strict=True)
        ]

        elapsed = time.monotonic() - start_time

        return GenerationResult(
            messages=timestamped_messages,
            chat_id=None,
            handles={},
            generation_time_seconds=elapsed,
            llm_provider_used=provider.name,
        )

    async def generate_to_database(
        self,
        personas: list[Persona],
        config: ConversationConfig,
        builder: DatabaseBuilder,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        result = await self.generate(personas, config, progress_callback)

        if progress_callback:
            progress_callback(
                GenerationProgress(
                    total_messages=config.message_count_target,
                    generated_messages=len(result.messages),
                    current_batch=0,
                    total_batches=0,
                    phase=GenerationPhase.WRITING_DATABASE,
                )
            )

        handle_map: dict[str, int] = {}

        for persona in personas:
            if not persona.is_self:
                handle_id = builder.add_handle(
                    identifier=persona.identifier,
                    service=config.service.value,
                )
                handle_map[persona.id] = handle_id

        handle_ids = list(handle_map.values())
        chat_type = "direct" if config.chat_type == ChatType.DIRECT else "group"

        chat_id = builder.create_chat(
            handles=handle_ids,
            chat_type=chat_type,
            service=config.service.value,
            display_name=config.name,
        )

        message_tuples = self._prepare_messages_for_db(
            result.messages,
            handle_map,
        )

        for i in range(0, len(message_tuples), DB_WRITE_CHUNK_SIZE):
            chunk = message_tuples[i : i + DB_WRITE_CHUNK_SIZE]
            builder.add_messages_batch(
                chat_id=chat_id,
                messages=chunk,
                service=config.service.value,
            )

        return GenerationResult(
            messages=result.messages,
            chat_id=chat_id,
            handles=handle_map,
            generation_time_seconds=result.generation_time_seconds,
            llm_provider_used=result.llm_provider_used,
        )

    async def _generate_all_messages(
        self,
        provider: LLMProvider,
        persona_descriptions: list[dict[str, str]],
        target_count: int,
        seed: str | None,
        progress_callback: ProgressCallback | None,
    ) -> list[GeneratedMessage]:
        messages: list[GeneratedMessage] = []
        batch_size = self.config.message_batch_size
        context_size = self.config.context_window_size
        total_batches = (target_count + batch_size - 1) // batch_size

        self_persona_id = next(
            (p["id"] for p in persona_descriptions if p.get("is_self") == "True"), None
        )

        self._partial_messages = []

        batch_num = 0
        while len(messages) < target_count:
            batch_num += 1
            remaining = target_count - len(messages)
            current_batch_size = min(batch_size, remaining)

            context = messages[-context_size:] if messages else []

            if progress_callback:
                progress_callback(
                    GenerationProgress(
                        total_messages=target_count,
                        generated_messages=len(messages),
                        current_batch=batch_num,
                        total_batches=total_batches,
                        phase=GenerationPhase.GENERATING,
                    )
                )

            batch = await self._generate_batch_with_retry(
                provider=provider,
                persona_descriptions=persona_descriptions,
                context=context,
                count=current_batch_size,
                seed=seed,
            )

            for msg in batch:
                msg.is_from_me = msg.sender_id == self_persona_id

            messages.extend(batch)
            self._partial_messages = messages.copy()

        return messages

    async def _generate_batch_with_retry(
        self,
        provider: LLMProvider,
        persona_descriptions: list[dict[str, str]],
        context: list[GeneratedMessage],
        count: int,
        seed: str | None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> list[GeneratedMessage]:
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                return await provider.generate_messages(
                    persona_descriptions=persona_descriptions,
                    context=context,
                    count=count,
                    seed=seed,
                )
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = 2**attempt
                    await asyncio.sleep(delay)

        raise LLMGenerationError(
            f"Failed after {max_retries} attempts: {last_error}",
            partial_messages=self._partial_messages,
        )

    def _format_personas_for_llm(
        self,
        personas: list[Persona],
    ) -> list[dict[str, str]]:
        return [
            {
                "id": p.id,
                "name": p.name,
                "personality": p.personality,
                "writing_style": p.writing_style,
                "emoji_usage": p.emoji_usage.value,
                "topics": ", ".join(p.topics_of_interest),
                "is_self": str(p.is_self),
            }
            for p in personas
        ]

    def _prepare_messages_for_db(
        self,
        messages: list[TimestampedMessage],
        handle_map: dict[str, int],
    ) -> list[tuple[int | None, str, bool, int]]:
        result: list[tuple[int | None, str, bool, int]] = []

        for tm in messages:
            msg = tm.message
            handle_id = None if msg.is_from_me else handle_map.get(msg.sender_id)
            result.append((handle_id, msg.text, msg.is_from_me, tm.timestamp))

        return result
