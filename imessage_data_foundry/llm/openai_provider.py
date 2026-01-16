import json

from openai import AsyncOpenAI

from imessage_data_foundry.llm.base import LLMProvider
from imessage_data_foundry.llm.config import LLMConfig
from imessage_data_foundry.llm.models import GeneratedMessage, GeneratedPersona, PersonaConstraints
from imessage_data_foundry.llm.prompts import PromptTemplates


class OpenAIProvider(LLMProvider):
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._client: AsyncOpenAI | None = None

    @property
    def name(self) -> str:
        return f"OpenAI ({self.config.openai_model})"

    @property
    def requires_api_key(self) -> bool:
        return True

    async def is_available(self) -> bool:
        return self.config.openai_api_key is not None

    def get_unavailability_reason(self) -> str | None:
        if self.config.openai_api_key is None:
            return "OPENAI_API_KEY not set"
        return None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.config.openai_api_key)
        return self._client

    async def generate_text(self, prompt: str, max_tokens: int = 150) -> str:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.config.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content or ""

    async def generate_personas(
        self,
        constraints: PersonaConstraints | None = None,
        count: int = 1,
    ) -> list[GeneratedPersona]:
        client = self._get_client()
        prompt = PromptTemplates.persona_generation(constraints, count)

        response = await client.chat.completions.create(
            model=self.config.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens_persona,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")

        data = json.loads(content)

        if count == 1 and isinstance(data, dict) and "personas" not in data:
            data = [data]
        elif isinstance(data, dict) and "personas" in data:
            data = data["personas"]

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

        response = await client.chat.completions.create(
            model=self.config.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens_messages,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")

        data = json.loads(content)

        if isinstance(data, dict) and "messages" in data:
            data = data["messages"]

        if not isinstance(data, list):
            raise ValueError(f"Expected list of messages, got: {type(data)}")

        return [GeneratedMessage.model_validate(m) for m in data]
