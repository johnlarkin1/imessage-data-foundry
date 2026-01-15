"""Local MLX-based LLM provider for Apple Silicon."""

from __future__ import annotations

import asyncio
import json
import re
from typing import TYPE_CHECKING, Any

from imessage_data_foundry.llm.base import LLMProvider
from imessage_data_foundry.llm.config import LLMConfig
from imessage_data_foundry.llm.models import GeneratedMessage, GeneratedPersona, PersonaConstraints
from imessage_data_foundry.llm.prompts import PromptTemplates

if TYPE_CHECKING:
    from mlx_lm.tokenizer_utils import TokenizerWrapper


class LocalMLXProvider(LLMProvider):
    """Local LLM provider using MLX on Apple Silicon."""

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
        try:
            import mlx_lm  # noqa: F401

            return True
        except ImportError:
            return False

    async def _ensure_model_loaded(self) -> None:
        if self._model is not None:
            return

        # Load synchronously to avoid Python 3.13 multiprocessing/tqdm fd issues
        # when running inside Textual. The model loading includes HuggingFace
        # downloads which use tqdm, and tqdm's multiprocessing lock creation
        # fails with "bad value(s) in fds_to_keep" when Textual has control of
        # the terminal file descriptors.
        self._model, self._tokenizer = self._load_model()

    def _load_model(self) -> tuple[Any, Any]:
        import os
        import threading

        # Workaround for Python 3.13 multiprocessing fd issues when running inside
        # Textual. tqdm tries to create multiprocessing locks which fail when
        # Textual controls terminal file descriptors. We replace the mp lock
        # with a threading lock which doesn't have this issue.
        import tqdm.std  # type: ignore[import-untyped]
        from mlx_lm import load

        original_create_mp_lock = tqdm.std.TqdmDefaultWriteLock.create_mp_lock

        def patched_create_mp_lock(cls: type) -> None:
            cls.mp_lock = threading.RLock()  # type: ignore[attr-defined]

        tqdm.std.TqdmDefaultWriteLock.create_mp_lock = classmethod(patched_create_mp_lock)  # type: ignore[assignment,arg-type]

        old_hf_disable = os.environ.get("HF_HUB_DISABLE_PROGRESS_BARS")
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        try:
            result = load(self._model_id)
            return result[0], result[1]
        finally:
            tqdm.std.TqdmDefaultWriteLock.create_mp_lock = original_create_mp_lock
            if old_hf_disable is None:
                os.environ.pop("HF_HUB_DISABLE_PROGRESS_BARS", None)
            else:
                os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = old_hf_disable

    def _generate_sync(self, prompt: str, max_tokens: int) -> str:
        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        if self._tokenizer is None or self._model is None:
            raise RuntimeError("Model not loaded")

        messages = [{"role": "user", "content": prompt}]
        formatted = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        sampler = make_sampler(temp=self.config.temperature)
        response = generate(
            self._model,
            self._tokenizer,
            prompt=formatted,
            max_tokens=max_tokens,
            sampler=sampler,
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
        response = await asyncio.to_thread(
            self._generate_sync, prompt, self.config.max_tokens_persona
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
        response = await asyncio.to_thread(
            self._generate_sync, prompt, self.config.max_tokens_messages
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
