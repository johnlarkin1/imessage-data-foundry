from imessage_data_foundry.llm.anthropic_provider import AnthropicProvider
from imessage_data_foundry.llm.base import LLMProvider
from imessage_data_foundry.llm.config import LLMConfig, ProviderType
from imessage_data_foundry.llm.local_provider import LocalMLXProvider
from imessage_data_foundry.llm.openai_provider import OpenAIProvider
from imessage_data_foundry.settings.storage import SettingsStorage


class ProviderNotAvailableError(Exception):
    """Raised when no LLM provider is available."""


class ProviderManager:
    """Manages LLM provider selection and fallback."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._providers: dict[ProviderType, LLMProvider] = {}

    def _get_provider_instance(self, provider_type: ProviderType) -> LLMProvider:
        if provider_type not in self._providers:
            if provider_type == ProviderType.LOCAL:
                self._providers[provider_type] = LocalMLXProvider(self.config)
            elif provider_type == ProviderType.OPENAI:
                self._providers[provider_type] = OpenAIProvider(self.config)
            elif provider_type == ProviderType.ANTHROPIC:
                self._providers[provider_type] = AnthropicProvider(self.config)
        return self._providers[provider_type]

    async def get_provider(
        self,
        preferred: ProviderType | None = None,
    ) -> LLMProvider:
        """Get the best available provider with fallback logic.

        Priority order:
        1. User's preferred provider (if specified and available)
        2. Stored provider preference from settings
        3. Default provider from config
        4. Local MLX (always try as fallback)
        5. OpenAI (if API key available)
        6. Anthropic (if API key available)

        Raises:
            ProviderNotAvailableError: If no provider is available
        """
        if preferred is None:
            with SettingsStorage() as storage:
                preferred = storage.get_provider()

        priority = [
            preferred or self.config.default_provider,
            ProviderType.LOCAL,
            ProviderType.OPENAI,
            ProviderType.ANTHROPIC,
        ]

        seen: set[ProviderType] = set()
        unique_priority = []
        for p in priority:
            if p not in seen:
                seen.add(p)
                unique_priority.append(p)

        errors: list[str] = []
        for provider_type in unique_priority:
            provider = self._get_provider_instance(provider_type)
            try:
                if await provider.is_available():
                    return provider
                reason = provider.get_unavailability_reason()
                if reason:
                    errors.append(f"  - {provider_type.value}: {reason}")
                else:
                    errors.append(f"  - {provider_type.value}: Not available")
            except Exception as e:
                errors.append(f"  - {provider_type.value}: {e}")

        error_details = "\n".join(errors) if errors else ""
        raise ProviderNotAvailableError(
            "No LLM provider available.\n\n"
            f"Tried providers:\n{error_details}\n\n"
            "Options:\n"
            "  1. Install mlx-lm for local inference: pip install mlx-lm\n"
            "  2. Set OPENAI_API_KEY environment variable\n"
            "  3. Set ANTHROPIC_API_KEY environment variable"
        )

    async def list_available_providers(self) -> list[tuple[ProviderType, str]]:
        """List all currently available providers with their display names."""
        available = []
        for provider_type in ProviderType:
            provider = self._get_provider_instance(provider_type)
            if await provider.is_available():
                available.append((provider_type, provider.name))
        return available

    async def list_all_providers(self) -> list[tuple[ProviderType, str, bool, str | None]]:
        """List all providers with availability status and reason.

        Returns list of (type, name, is_available, unavailability_reason).
        """
        results = []
        for provider_type in ProviderType:
            provider = self._get_provider_instance(provider_type)
            is_available = await provider.is_available()
            reason = None if is_available else provider.get_unavailability_reason()
            results.append((provider_type, provider.name, is_available, reason))
        return results

    async def get_provider_by_type(self, provider_type: ProviderType) -> LLMProvider:
        """Get a specific provider by type.

        Raises:
            ProviderNotAvailableError: If the requested provider is not available
        """
        provider = self._get_provider_instance(provider_type)
        if not await provider.is_available():
            raise ProviderNotAvailableError(
                f"Provider {provider_type.value} is not available. "
                f"{'Set the API key.' if provider.requires_api_key else 'Install mlx-lm.'}"
            )
        return provider
