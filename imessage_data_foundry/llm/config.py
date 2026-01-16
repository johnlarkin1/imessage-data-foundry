from enum import Enum
from pathlib import Path

import psutil
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderType(str, Enum):
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LocalModelSize(str, Enum):
    AUTO = "auto"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


MODEL_MAP: dict[LocalModelSize, str] = {
    LocalModelSize.SMALL: "mlx-community/Llama-3.2-3B-Instruct-4bit",
    LocalModelSize.MEDIUM: "mlx-community/Qwen2.5-3B-Instruct-4bit",
    LocalModelSize.LARGE: "mlx-community/Qwen2.5-7B-Instruct-4bit",
}


def get_system_ram_gb() -> float:
    return psutil.virtual_memory().total / (1024**3)


def auto_select_model_size() -> LocalModelSize:
    ram_gb = get_system_ram_gb()
    if ram_gb >= 24:
        return LocalModelSize.LARGE
    elif ram_gb >= 16:
        return LocalModelSize.MEDIUM
    else:
        return LocalModelSize.SMALL


def resolve_model_id(size: LocalModelSize, override_id: str | None = None) -> str:
    if override_id:
        return override_id
    if size == LocalModelSize.AUTO:
        size = auto_select_model_size()
    return MODEL_MAP[size]


class LLMConfig(BaseSettings):
    """Configuration for LLM providers."""

    model_config = SettingsConfigDict(
        env_prefix="IMESSAGE_FOUNDRY_",
        env_file=".env",
        extra="ignore",
    )

    default_provider: ProviderType = ProviderType.LOCAL
    local_model_size: LocalModelSize = LocalModelSize.AUTO
    local_model_id: str | None = None
    local_cache_dir: Path | None = None

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    openai_model: str = "gpt-5-nano"
    anthropic_model: str = "claude-3-5-haiku-20241022"

    temperature: float = 0.8
    max_tokens_persona: int = 1024
    max_tokens_messages: int = 4096
    message_batch_size: int = 10
    context_window_size: int = 10

    def get_local_model_id(self) -> str:
        return resolve_model_id(self.local_model_size, self.local_model_id)
