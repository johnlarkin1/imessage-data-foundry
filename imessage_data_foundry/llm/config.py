"""LLM configuration using pydantic-settings."""

from enum import Enum
from pathlib import Path

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
    LocalModelSize.MEDIUM: "mlx-community/Qwen3-4B-Instruct-2507-4bit",
    LocalModelSize.LARGE: "mlx-community/Qwen3-8B-Instruct-4bit",
}


def get_system_ram_gb() -> float:
    try:
        import psutil

        return psutil.virtual_memory().total / (1024**3)
    except ImportError:
        return 8.0


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

    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-haiku-20240307"

    temperature: float = 0.8
    max_tokens_persona: int = 1024
    max_tokens_messages: int = 2048
    message_batch_size: int = 30
    context_window_size: int = 15

    def get_local_model_id(self) -> str:
        return resolve_model_id(self.local_model_size, self.local_model_id)
