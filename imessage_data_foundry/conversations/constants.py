from dataclasses import dataclass

# Circadian rhythm weights: (start_hour, end_hour, activity_weight)
# Higher weight = more likely to send messages during that time
CIRCADIAN_WEIGHTS: list[tuple[int, int, float]] = [
    (0, 6, 0.05),  # Late night / early morning
    (6, 8, 0.30),  # Early morning wake-up
    (8, 9, 0.70),  # Morning commute
    (9, 12, 0.90),  # Morning work hours
    (12, 14, 0.80),  # Lunch break
    (14, 18, 0.95),  # Afternoon work
    (18, 21, 1.00),  # Evening peak
    (21, 23, 0.70),  # Late evening
    (23, 24, 0.30),  # Night wind-down
]
DEFAULT_CIRCADIAN_WEIGHT = 0.5

# Jitter multiplier range for natural timing variation
JITTER_RANGE = (0.7, 1.3)
RESPONSE_JITTER_RANGE = (0.8, 1.2)

# Session message delays (seconds) for special response time personas
INSTANT_RESPONSE_DELAY_RANGE = (5, 45)
SLOW_RESPONSE_DELAY_RANGE = (60, 180)

# Weighted time selection
MAX_WEIGHTED_TIME_ATTEMPTS = 50


@dataclass
class TopicShiftConfig:
    min_messages: int = 20
    early_progress_threshold: float = 0.2
    late_progress_threshold: float = 0.9
    mid_conversation_start: float = 0.4
    mid_conversation_end: float = 0.6
    base_shift_chance: float = 0.02
    peak_shift_chance: float = 0.05


TOPIC_SHIFT = TopicShiftConfig()

# Seed parsing
MAX_SEED_THEMES = 5
MIN_THEME_WORD_LENGTH = 3

# Database operations
DB_WRITE_CHUNK_SIZE = 500
DEFAULT_MAX_RETRIES = 3
