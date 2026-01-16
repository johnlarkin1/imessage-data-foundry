import json
import re
from typing import Any

from anthropic import AsyncAnthropic

from imessage_data_foundry.llm.base import LLMProvider
from imessage_data_foundry.llm.config import LLMConfig
from imessage_data_foundry.llm.models import (
    GeneratedMessage,
    GeneratedPersona,
    PersonaConstraints,
)
from imessage_data_foundry.llm.prompts import PromptTemplates


class AnthropicProvider(LLMProvider):
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._client: AsyncAnthropic | None = None

    @property
    def name(self) -> str:
        return f"Anthropic ({self.config.anthropic_model})"

    @property
    def requires_api_key(self) -> bool:
        return True

    async def is_available(self) -> bool:
        return self.config.anthropic_api_key is not None

    def get_unavailability_reason(self) -> str | None:
        if self.config.anthropic_api_key is None:
            return "ANTHROPIC_API_KEY not set"
        return None

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.config.anthropic_api_key)
        return self._client

    async def generate_text(self, prompt: str, max_tokens: int = 150) -> str:
        client = self._get_client()
        response = await client.messages.create(
            model=self.config.anthropic_model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        if response.content and hasattr(response.content[0], "text"):
            return response.content[0].text  # type: ignore[union-attr]
        return ""

    def _extract_json(self, text: str) -> Any:
        text = text.strip()
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            text = json_match.group(1).strip()
        bracket_match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", text)
        if bracket_match:
            text = bracket_match.group(1)
        return json.loads(text)

    async def generate_personas(
        self,
        constraints: PersonaConstraints | None = None,
        count: int = 1,
    ) -> list[GeneratedPersona]:
        client = self._get_client()
        prompt = PromptTemplates.persona_generation(constraints, count)

        response = await client.messages.create(
            model=self.config.anthropic_model,
            max_tokens=self.config.max_tokens_persona,
            messages=[{"role": "user", "content": prompt}],
        )

        content = ""
        if response.content and hasattr(response.content[0], "text"):
            content = response.content[0].text  # type: ignore[union-attr]
        if not content:
            raise ValueError("Empty response from Anthropic")

        try:
            data = self._extract_json(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse response as JSON: {e}\nResponse: {content}") from e

        if count == 1 and isinstance(data, dict):
            data = [data]

        if not isinstance(data, list):
            raise ValueError(f"Expected list of personas, got: {type(data)}")

        return [GeneratedPersona.model_validate(p) for p in data]

    async def generate_messages(
        self,
        persona_descriptions: list[dict[str, str]],
        context: list[GeneratedMessage],
        count: int,
        seed: str | None = None,
    ) -> list[GeneratedMessage]:
        client = self._get_client()
        prompt = PromptTemplates.message_generation(persona_descriptions, context, count, seed)

        response = await client.messages.create(
            model=self.config.anthropic_model,
            max_tokens=self.config.max_tokens_messages,
            messages=[{"role": "user", "content": prompt}],
        )

        content = ""
        if response.content and hasattr(response.content[0], "text"):
            content = response.content[0].text  # type: ignore[union-attr]
        if not content:
            raise ValueError("Empty response from Anthropic")

        try:
            data = self._extract_json(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse response as JSON: {e}\nResponse: {content}") from e

        if not isinstance(data, list):
            raise ValueError(f"Expected list of messages, got: {type(data)}")

        return [GeneratedMessage.model_validate(m) for m in data]
