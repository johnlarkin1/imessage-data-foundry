from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from imessage_data_foundry.llm.models import GeneratedMessage, GeneratedPersona, PersonaConstraints


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""

    @property
    @abstractmethod
    def requires_api_key(self) -> bool:
        """Whether this provider requires an API key."""

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this provider is available (API key set, model downloaded, etc.)."""

    @abstractmethod
    async def generate_personas(
        self,
        constraints: PersonaConstraints | None = None,
        count: int = 1,
    ) -> list[GeneratedPersona]:
        """Generate one or more personas with optional constraints.

        Args:
            constraints: Optional constraints for persona generation
            count: Number of personas to generate

        Returns:
            List of generated persona data (not yet full Persona models)
        """

    @abstractmethod
    async def generate_messages(
        self,
        persona_descriptions: list[dict[str, str]],
        context: list[GeneratedMessage],
        count: int,
        seed: str | None = None,
    ) -> list[GeneratedMessage]:
        """Generate a batch of messages for a conversation.

        Args:
            persona_descriptions: List of dicts with persona info for prompting
            context: Recent messages for context continuity
            count: Number of messages to generate
            seed: Optional conversation theme/seed

        Returns:
            List of generated messages
        """

    async def stream_messages(
        self,
        persona_descriptions: list[dict[str, str]],
        context: list[GeneratedMessage],
        count: int,
        seed: str | None = None,
    ) -> AsyncIterator[GeneratedMessage]:
        """Stream messages one at a time for progress feedback.

        Default implementation just yields from generate_messages.
        Providers can override for true streaming.
        """
        messages = await self.generate_messages(persona_descriptions, context, count, seed)
        for msg in messages:
            yield msg
