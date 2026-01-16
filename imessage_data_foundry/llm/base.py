from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from imessage_data_foundry.llm.models import GeneratedMessage, GeneratedPersona, PersonaConstraints


class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def requires_api_key(self) -> bool: ...

    @abstractmethod
    async def is_available(self) -> bool: ...

    def get_unavailability_reason(self) -> str | None:
        """Return reason why provider is unavailable, or None if available."""
        return None

    @abstractmethod
    async def generate_text(self, prompt: str, max_tokens: int = 150) -> str: ...

    @abstractmethod
    async def generate_personas(
        self,
        constraints: PersonaConstraints | None = None,
        count: int = 1,
    ) -> list[GeneratedPersona]: ...

    @abstractmethod
    async def generate_messages(
        self,
        persona_descriptions: list[dict[str, str]],
        context: list[GeneratedMessage],
        count: int,
        seed: str | None = None,
    ) -> list[GeneratedMessage]: ...

    async def stream_messages(
        self,
        persona_descriptions: list[dict[str, str]],
        context: list[GeneratedMessage],
        count: int,
        seed: str | None = None,
    ) -> AsyncIterator[GeneratedMessage]:
        messages = await self.generate_messages(persona_descriptions, context, count, seed)
        for msg in messages:
            yield msg
