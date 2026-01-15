import random
from dataclasses import dataclass, field

from imessage_data_foundry.personas.models import Persona


@dataclass
class ConversationSeed:
    raw_seed: str | None = None
    themes: list[str] = field(default_factory=list)
    opening_context: str | None = None


def parse_seed(seed: str | None) -> ConversationSeed:
    """Parse user-provided seed into structured components."""
    if not seed or not seed.strip():
        return ConversationSeed()

    seed = seed.strip()
    themes = [word.strip() for word in seed.split() if len(word.strip()) > 3]

    return ConversationSeed(
        raw_seed=seed,
        themes=themes[:5],
        opening_context=seed,
    )


def should_introduce_topic_shift(
    message_index: int,
    total_messages: int,
    rng: random.Random,
) -> bool:
    """Determine if a natural topic shift should occur."""
    if total_messages < 20:
        return False

    progress = message_index / total_messages

    if progress < 0.2:
        return False

    if progress > 0.9:
        return False

    base_chance = 0.02
    if 0.4 <= progress <= 0.6:
        base_chance = 0.05

    return rng.random() < base_chance


def get_topic_shift_hint(
    personas: list[Persona],
    current_themes: list[str],
    rng: random.Random,
) -> str | None:
    """Generate a hint for topic shift based on persona interests."""
    all_topics: list[str] = []
    for persona in personas:
        all_topics.extend(persona.topics_of_interest)

    available = [t for t in all_topics if t.lower() not in [c.lower() for c in current_themes]]

    if not available:
        return None

    return rng.choice(available)
