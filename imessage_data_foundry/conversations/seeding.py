import random
from dataclasses import dataclass, field

from imessage_data_foundry.conversations.constants import (
    MAX_SEED_THEMES,
    MIN_THEME_WORD_LENGTH,
    TOPIC_SHIFT,
)
from imessage_data_foundry.personas.models import Persona


@dataclass
class ConversationSeed:
    raw_seed: str | None = None
    themes: list[str] = field(default_factory=list)
    opening_context: str | None = None


def parse_seed(seed: str | None) -> ConversationSeed:
    if not seed or not seed.strip():
        return ConversationSeed()

    seed = seed.strip()
    themes = [word.strip() for word in seed.split() if len(word.strip()) > MIN_THEME_WORD_LENGTH]

    return ConversationSeed(
        raw_seed=seed,
        themes=themes[:MAX_SEED_THEMES],
        opening_context=seed,
    )


def should_introduce_topic_shift(
    message_index: int,
    total_messages: int,
    rng: random.Random,
) -> bool:
    if total_messages < TOPIC_SHIFT.min_messages:
        return False

    progress = message_index / total_messages

    if progress < TOPIC_SHIFT.early_progress_threshold:
        return False

    if progress > TOPIC_SHIFT.late_progress_threshold:
        return False

    base_chance = TOPIC_SHIFT.base_shift_chance
    if TOPIC_SHIFT.mid_conversation_start <= progress <= TOPIC_SHIFT.mid_conversation_end:
        base_chance = TOPIC_SHIFT.peak_shift_chance

    return rng.random() < base_chance


def get_topic_shift_hint(
    personas: list[Persona],
    current_themes: list[str],
    rng: random.Random,
) -> str | None:
    all_topics: list[str] = []
    for persona in personas:
        all_topics.extend(persona.topics_of_interest)

    available = [t for t in all_topics if t.lower() not in [c.lower() for c in current_themes]]

    if not available:
        return None

    return rng.choice(available)
