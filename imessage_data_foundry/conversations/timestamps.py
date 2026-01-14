"""Realistic timestamp distribution for conversation generation."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from imessage_data_foundry.personas.models import ResponseTime
from imessage_data_foundry.utils.apple_time import datetime_to_apple_ns

if TYPE_CHECKING:
    from imessage_data_foundry.personas.models import Persona


RESPONSE_TIME_RANGES: dict[ResponseTime, tuple[int, int]] = {
    ResponseTime.INSTANT: (5, 60),
    ResponseTime.MINUTES: (60, 600),
    ResponseTime.HOURS: (1800, 14400),
    ResponseTime.DAYS: (43200, 172800),
}

CIRCADIAN_WEIGHTS: list[tuple[int, int, float]] = [
    (0, 6, 0.05),
    (6, 8, 0.30),
    (8, 9, 0.70),
    (9, 12, 0.90),
    (12, 14, 0.80),
    (14, 18, 0.95),
    (18, 21, 1.00),
    (21, 23, 0.70),
    (23, 24, 0.30),
]


@dataclass
class TimestampConfig:
    session_ratio: float = 0.70
    min_session_size: int = 5
    max_session_size: int = 30
    min_session_gap_seconds: int = 30
    max_session_gap_seconds: int = 300


@dataclass
class Session:
    start_index: int
    size: int


def generate_timestamps(
    start: datetime,
    end: datetime,
    count: int,
    personas: list[Persona],
    seed: int | None = None,
) -> list[int]:
    """Generate realistic message timestamps as Apple epoch nanoseconds."""
    if count <= 0:
        return []

    if end <= start:
        raise ValueError("end must be after start")

    rng = random.Random(seed)
    config = TimestampConfig()

    total_seconds = (end - start).total_seconds()
    if total_seconds < count:
        raise ValueError("Time range too short for message count")

    sessions = _plan_sessions(count, config, rng)
    timestamps: list[datetime] = []

    session_timestamps = _generate_session_timestamps(start, end, sessions, personas, config, rng)
    timestamps.extend(session_timestamps)

    scattered_count = count - len(timestamps)
    if scattered_count > 0:
        scattered = _generate_scattered_timestamps(start, end, scattered_count, rng)
        timestamps.extend(scattered)

    timestamps.sort()

    return [datetime_to_apple_ns(ts) for ts in timestamps]


def _plan_sessions(
    count: int,
    config: TimestampConfig,
    rng: random.Random,
) -> list[Session]:
    """Plan session structure for the conversation."""
    session_message_count = int(count * config.session_ratio)
    if session_message_count < config.min_session_size:
        return []

    sessions: list[Session] = []
    remaining = session_message_count
    current_index = 0

    while remaining >= config.min_session_size:
        max_size = min(config.max_session_size, remaining)
        size = rng.randint(config.min_session_size, max_size)
        sessions.append(Session(start_index=current_index, size=size))
        current_index += size
        remaining -= size

    return sessions


def _generate_session_timestamps(
    start: datetime,
    end: datetime,
    sessions: list[Session],
    personas: list[Persona],
    config: TimestampConfig,
    rng: random.Random,
) -> list[datetime]:
    """Generate timestamps for all sessions."""
    if not sessions:
        return []

    timestamps: list[datetime] = []
    total_seconds = (end - start).total_seconds()
    num_sessions = len(sessions)

    slot_duration = total_seconds / (num_sessions + 1)

    for i, session in enumerate(sessions):
        slot_start = start + timedelta(seconds=slot_duration * i)
        slot_end = start + timedelta(seconds=slot_duration * (i + 1))

        session_start = _pick_weighted_time(slot_start, slot_end, rng)

        session_ts = _generate_single_session(session_start, session.size, personas, config, rng)
        timestamps.extend(session_ts)

    return timestamps


def _generate_single_session(
    start: datetime,
    size: int,
    personas: list[Persona],
    config: TimestampConfig,
    rng: random.Random,
) -> list[datetime]:
    """Generate timestamps for a single session."""
    timestamps = [start]
    current = start

    for i in range(1, size):
        persona = personas[i % len(personas)] if personas else None
        delay = _get_session_delay(persona, config, rng)
        current = current + delay
        timestamps.append(current)

    return timestamps


def _get_session_delay(
    persona: Persona | None,
    config: TimestampConfig,
    rng: random.Random,
) -> timedelta:
    """Get delay between messages in a session."""
    if persona and persona.typical_response_time == ResponseTime.INSTANT:
        base_delay = rng.randint(5, 45)
    elif persona and persona.typical_response_time == ResponseTime.DAYS:
        base_delay = rng.randint(60, 180)
    else:
        base_delay = rng.randint(config.min_session_gap_seconds, config.max_session_gap_seconds)

    jitter = rng.uniform(0.7, 1.3)
    return timedelta(seconds=int(base_delay * jitter))


def _generate_scattered_timestamps(
    start: datetime,
    end: datetime,
    count: int,
    rng: random.Random,
) -> list[datetime]:
    """Generate scattered messages between sessions."""
    timestamps: list[datetime] = []

    for _ in range(count):
        ts = _pick_weighted_time(start, end, rng)
        timestamps.append(ts)

    return timestamps


def _pick_weighted_time(
    start: datetime,
    end: datetime,
    rng: random.Random,
    max_attempts: int = 50,
) -> datetime:
    """Pick a time weighted by circadian rhythm."""
    for _ in range(max_attempts):
        random_seconds = rng.uniform(0, (end - start).total_seconds())
        candidate = start + timedelta(seconds=random_seconds)

        weight = _get_circadian_weight(candidate.hour)
        if rng.random() < weight:
            return candidate

    random_seconds = rng.uniform(0, (end - start).total_seconds())
    return start + timedelta(seconds=random_seconds)


def _get_circadian_weight(hour: int) -> float:
    """Get weight for a given hour based on circadian rhythm."""
    for start_hour, end_hour, weight in CIRCADIAN_WEIGHTS:
        if start_hour <= hour < end_hour:
            return weight
    return 0.5


def get_response_delay(
    persona: Persona,
    rng: random.Random | None = None,
) -> timedelta:
    """Get a realistic response delay based on persona's response time setting."""
    if rng is None:
        rng = random.Random()

    min_seconds, max_seconds = RESPONSE_TIME_RANGES.get(persona.typical_response_time, (60, 600))

    delay_seconds = rng.randint(min_seconds, max_seconds)
    jitter = rng.uniform(0.8, 1.2)

    return timedelta(seconds=int(delay_seconds * jitter))
