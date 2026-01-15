import asyncio
import json
import re
from typing import Any

from mlx_lm import generate as mlx_generate
from mlx_lm import load as mlx_load
from mlx_lm.tokenizer_utils import TokenizerWrapper

from imessage_data_foundry.llm.base import LLMProvider
from imessage_data_foundry.llm.config import LLMConfig
from imessage_data_foundry.llm.models import GeneratedMessage, GeneratedPersona, PersonaConstraints
from imessage_data_foundry.llm.prompts import PromptTemplates


class LocalMLXProvider(LLMProvider):
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._model: Any = None
        self._tokenizer: TokenizerWrapper | None = None
        self._model_id = self.config.get_local_model_id()

    @property
    def name(self) -> str:
        return f"Local MLX ({self._model_id.split('/')[-1]})"

    @property
    def requires_api_key(self) -> bool:
        return False

    async def is_available(self) -> bool:
        return True

    async def _ensure_model_loaded(self) -> None:
        if self._model is not None:
            return

        loop = asyncio.get_event_loop()
        self._model, self._tokenizer = await loop.run_in_executor(None, self._load_model)

    def _load_model(self) -> tuple[Any, Any]:
        result = mlx_load(self._model_id)
        return result[0], result[1]

    def _generate_sync(self, prompt: str, max_tokens: int) -> str:
        if self._tokenizer is None or self._model is None:
            raise RuntimeError("Model not loaded")

        messages = [{"role": "user", "content": prompt}]
        formatted = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        response = mlx_generate(
            self._model,
            self._tokenizer,
            prompt=formatted,
            max_tokens=max_tokens,
            temp=self.config.temperature,
            verbose=False,
        )
        return response

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
        await self._ensure_model_loaded()

        prompt = PromptTemplates.persona_generation(constraints, count)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, self._generate_sync, prompt, self.config.max_tokens_persona
        )

        try:
            data = self._extract_json(response)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse LLM response as JSON: {e}\nResponse: {response}"
            ) from e

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
        await self._ensure_model_loaded()

        prompt = PromptTemplates.message_generation(persona_descriptions, context, count, seed)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, self._generate_sync, prompt, self.config.max_tokens_messages
        )

        try:
            data = self._extract_json(response)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse LLM response as JSON: {e}\nResponse: {response}"
            ) from e

        if not isinstance(data, list):
            raise ValueError(f"Expected list of messages, got: {type(data)}")

        return [GeneratedMessage.model_validate(m) for m in data]
