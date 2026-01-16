import asyncio
import concurrent.futures
from dataclasses import dataclass
from enum import Enum

from imessage_data_foundry.llm.base import LLMProvider
from imessage_data_foundry.llm.manager import ProviderManager


class AutocompleteField(Enum):
    PERSONALITY = "personality"
    WRITING_STYLE = "writing_style"
    RELATIONSHIP = "relationship"
    TOPICS = "topics"


@dataclass
class AutocompleteContext:
    field: AutocompleteField
    name: str | None = None
    is_self: bool = False
    existing_values: dict[str, str] | None = None


_cached_provider: LLMProvider | None = None


async def _get_provider() -> LLMProvider | None:
    global _cached_provider
    if _cached_provider is not None:
        return _cached_provider
    try:
        manager = ProviderManager()
        _cached_provider = await manager.get_provider()
        return _cached_provider
    except Exception:
        return None


def _build_prompt(context: AutocompleteContext, current_text: str) -> str:
    name = context.name or "this person"
    existing = context.existing_values or {}

    if context.field == AutocompleteField.PERSONALITY:
        if context.is_self:
            prompt = f"""Generate a realistic personality description for a person named {name} who texts their friends.
This is for creating fake iMessage data. Describe them as a real human, NOT an AI.
Write 2-3 sentences in third person about their personality traits, interests, and how they interact with friends.
Examples:
- "Laid-back and always up for spontaneous plans. Loves sharing memes and usually responds quickly. Gets really into whatever hobby they're currently obsessed with."
- "A bit of a workaholic but makes time for close friends. Thoughtful texter who remembers details. Tends to send long messages."
"""
        else:
            prompt = f"""Generate a realistic personality description for a fictional person named {name}.
This is for creating fake iMessage data. Write 2-3 sentences in third person describing their personality.
Examples:
- "Outgoing and energetic, always planning the next get-together. Quick to respond and loves using voice messages."
- "Quiet but witty, prefers deep conversations over small talk. Takes time to respond but always thoughtful."
"""
        if current_text:
            prompt += f"\nBuild on this start: '{current_text}'"
        prompt += "\nReturn ONLY the personality description, nothing else."
        return prompt

    elif context.field == AutocompleteField.WRITING_STYLE:
        personality = existing.get("personality", "")
        prompt = f"Describe {name}'s texting style in a few words (e.g., 'casual, uses abbreviations like lol and tbh', 'proper grammar, rarely uses emojis', 'lots of emojis and exclamation points!')."
        if personality:
            prompt += f" Their personality: {personality}"
        if current_text:
            prompt += f" Build on: '{current_text}'"
        prompt += " Return ONLY the style description, 5-15 words."
        return prompt

    elif context.field == AutocompleteField.RELATIONSHIP:
        prompt = "Suggest a realistic relationship type (e.g., college friend, coworker, sister, old roommate, gym buddy, neighbor)."
        if current_text:
            prompt += f" Build on: '{current_text}'"
        prompt += " Return ONLY the relationship, 1-3 words."
        return prompt

    elif context.field == AutocompleteField.TOPICS:
        personality = existing.get("personality", "")
        relationship = existing.get("relationship", "")
        prompt = f"Suggest 3-5 realistic topics that {name} might text about with friends."
        if personality:
            prompt += f" Their personality: {personality}"
        if relationship:
            prompt += f" Relationship: {relationship}"
        if current_text:
            prompt += f" Build on: '{current_text}'"
        prompt += " Return ONLY comma-separated topics (e.g., 'weekend plans, work gossip, Netflix shows, fitness')."
        return prompt

    return f"Complete this text: {current_text}"


async def generate_autocomplete(context: AutocompleteContext, current_text: str = "") -> str | None:
    provider = await _get_provider()
    if provider is None:
        return None

    prompt = _build_prompt(context, current_text)
    try:
        result = await provider.generate_text(prompt, max_tokens=100)
        result = result.strip().strip('"').strip("'")
        return result
    except Exception:
        return None


def generate_autocomplete_sync(context: AutocompleteContext, current_text: str = "") -> str | None:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, generate_autocomplete(context, current_text))
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(generate_autocomplete(context, current_text))
    except Exception:
        try:
            return asyncio.run(generate_autocomplete(context, current_text))
        except Exception:
            return None
