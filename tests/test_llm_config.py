import os
from unittest.mock import patch

from imessage_data_foundry.llm.config import (
    MODEL_MAP,
    LLMConfig,
    LocalModelSize,
    ProviderType,
    auto_select_model_size,
    get_system_ram_gb,
    resolve_model_id,
)


class TestProviderType:
    def test_provider_types_exist(self):
        assert ProviderType.LOCAL == "local"
        assert ProviderType.OPENAI == "openai"
        assert ProviderType.ANTHROPIC == "anthropic"

    def test_provider_type_values(self):
        assert len(ProviderType) == 3


class TestLocalModelSize:
    def test_model_sizes_exist(self):
        assert LocalModelSize.AUTO == "auto"
        assert LocalModelSize.SMALL == "small"
        assert LocalModelSize.MEDIUM == "medium"
        assert LocalModelSize.LARGE == "large"

    def test_model_map_has_all_sizes(self):
        assert LocalModelSize.SMALL in MODEL_MAP
        assert LocalModelSize.MEDIUM in MODEL_MAP
        assert LocalModelSize.LARGE in MODEL_MAP
        assert LocalModelSize.AUTO not in MODEL_MAP


class TestAutoSelectModelSize:
    def test_auto_select_low_ram(self):
        with patch("imessage_data_foundry.llm.config.get_system_ram_gb", return_value=8.0):
            size = auto_select_model_size()
            assert size == LocalModelSize.SMALL

    def test_auto_select_medium_ram(self):
        with patch("imessage_data_foundry.llm.config.get_system_ram_gb", return_value=16.0):
            size = auto_select_model_size()
            assert size == LocalModelSize.MEDIUM

    def test_auto_select_high_ram(self):
        with patch("imessage_data_foundry.llm.config.get_system_ram_gb", return_value=32.0):
            size = auto_select_model_size()
            assert size == LocalModelSize.LARGE


class TestResolveModelId:
    def test_resolve_with_override(self):
        model_id = resolve_model_id(LocalModelSize.SMALL, "custom/model")
        assert model_id == "custom/model"

    def test_resolve_small(self):
        model_id = resolve_model_id(LocalModelSize.SMALL)
        assert model_id == MODEL_MAP[LocalModelSize.SMALL]

    def test_resolve_medium(self):
        model_id = resolve_model_id(LocalModelSize.MEDIUM)
        assert model_id == MODEL_MAP[LocalModelSize.MEDIUM]

    def test_resolve_large(self):
        model_id = resolve_model_id(LocalModelSize.LARGE)
        assert model_id == MODEL_MAP[LocalModelSize.LARGE]

    def test_resolve_auto(self):
        with patch("imessage_data_foundry.llm.config.auto_select_model_size") as mock:
            mock.return_value = LocalModelSize.MEDIUM
            model_id = resolve_model_id(LocalModelSize.AUTO)
            assert model_id == MODEL_MAP[LocalModelSize.MEDIUM]
            mock.assert_called_once()


class TestLLMConfig:
    def test_default_values(self):
        config = LLMConfig()
        assert config.default_provider == ProviderType.LOCAL
        assert config.local_model_size == LocalModelSize.AUTO
        assert config.local_model_id is None
        assert config.temperature == 0.8
        assert config.message_batch_size == 10
        assert config.context_window_size == 10

    def test_openai_model_default(self):
        config = LLMConfig()
        assert config.openai_model == "gpt-5-nano"

    def test_anthropic_model_default(self):
        config = LLMConfig()
        assert config.anthropic_model == "claude-3-5-haiku-20241022"

    def test_get_local_model_id(self):
        config = LLMConfig(local_model_size=LocalModelSize.SMALL)
        model_id = config.get_local_model_id()
        assert model_id == MODEL_MAP[LocalModelSize.SMALL]

    def test_get_local_model_id_with_override(self):
        config = LLMConfig(local_model_id="custom/model")
        model_id = config.get_local_model_id()
        assert model_id == "custom/model"

    def test_api_keys_none_by_default(self):
        config = LLMConfig()
        assert config.openai_api_key is None
        assert config.anthropic_api_key is None

    def test_env_prefix(self):
        with patch.dict(os.environ, {"IMESSAGE_FOUNDRY_TEMPERATURE": "0.5"}):
            config = LLMConfig()
            assert config.temperature == 0.5


class TestGetSystemRamGb:
    def test_returns_float(self):
        ram = get_system_ram_gb()
        assert isinstance(ram, float)
        assert ram > 0
