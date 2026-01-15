from unittest.mock import AsyncMock, MagicMock

import pytest

from imessage_data_foundry.llm.config import LLMConfig, ProviderType
from imessage_data_foundry.llm.manager import ProviderManager, ProviderNotAvailableError


class TestProviderManager:
    def test_init_default_config(self):
        manager = ProviderManager()
        assert manager.config is not None
        assert isinstance(manager.config, LLMConfig)

    def test_init_with_config(self):
        config = LLMConfig(temperature=0.5)
        manager = ProviderManager(config)
        assert manager.config.temperature == 0.5


class TestGetProvider:
    @pytest.mark.asyncio
    async def test_get_provider_local_available(self):
        manager = ProviderManager()
        provider = await manager.get_provider()
        assert provider is not None

    @pytest.mark.asyncio
    async def test_get_provider_no_available_raises(self):
        manager = ProviderManager()

        mock_local = MagicMock()
        mock_local.is_available = AsyncMock(return_value=False)
        mock_openai = MagicMock()
        mock_openai.is_available = AsyncMock(return_value=False)
        mock_anthropic = MagicMock()
        mock_anthropic.is_available = AsyncMock(return_value=False)

        manager._providers[ProviderType.LOCAL] = mock_local
        manager._providers[ProviderType.OPENAI] = mock_openai
        manager._providers[ProviderType.ANTHROPIC] = mock_anthropic

        with pytest.raises(ProviderNotAvailableError):
            await manager.get_provider()


class TestListAvailableProviders:
    @pytest.mark.asyncio
    async def test_list_returns_tuples(self):
        manager = ProviderManager()
        providers = await manager.list_available_providers()
        assert isinstance(providers, list)
        for item in providers:
            assert isinstance(item, tuple)
            assert len(item) == 2

    @pytest.mark.asyncio
    async def test_list_returns_names(self):
        manager = ProviderManager()
        providers = await manager.list_available_providers()
        for _, name in providers:
            assert isinstance(name, str)
            assert len(name) > 0


class TestGetProviderByType:
    @pytest.mark.asyncio
    async def test_get_specific_provider_local(self):
        manager = ProviderManager()
        provider = await manager.get_provider_by_type(ProviderType.LOCAL)
        assert provider is not None

    @pytest.mark.asyncio
    async def test_get_unavailable_raises(self):
        manager = ProviderManager()

        mock_local = MagicMock()
        mock_local.is_available = AsyncMock(return_value=False)
        mock_local.requires_api_key = False
        manager._providers[ProviderType.LOCAL] = mock_local

        with pytest.raises(ProviderNotAvailableError):
            await manager.get_provider_by_type(ProviderType.LOCAL)


class TestProviderNotAvailableError:
    def test_error_message(self):
        error = ProviderNotAvailableError("Test message")
        assert str(error) == "Test message"

    def test_error_is_exception(self):
        assert issubclass(ProviderNotAvailableError, Exception)
