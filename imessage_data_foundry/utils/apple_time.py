from datetime import UTC, datetime

APPLE_EPOCH_OFFSET: int = 978307200
NANOSECONDS_PER_SECOND: int = 1_000_000_000


def unix_to_apple_seconds(unix_ts: float) -> int:
    """Convert Unix timestamp to Apple epoch seconds."""
    return int(unix_ts - APPLE_EPOCH_OFFSET)


def apple_seconds_to_unix(apple_ts: int) -> float:
    """Convert Apple epoch seconds to Unix timestamp."""
    return float(apple_ts + APPLE_EPOCH_OFFSET)


def unix_to_apple_ns(unix_ts: float) -> int:
    """Convert Unix timestamp to Apple epoch nanoseconds."""
    apple_seconds = unix_ts - APPLE_EPOCH_OFFSET
    return int(apple_seconds * NANOSECONDS_PER_SECOND)


def apple_ns_to_unix(apple_ns: int) -> float:
    """Convert Apple epoch nanoseconds to Unix timestamp."""
    apple_seconds = apple_ns / NANOSECONDS_PER_SECOND
    return apple_seconds + APPLE_EPOCH_OFFSET


def datetime_to_apple_ns(dt: datetime) -> int:
    """Convert datetime to Apple epoch nanoseconds."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    unix_ts = dt.timestamp()
    return unix_to_apple_ns(unix_ts)


def apple_ns_to_datetime(apple_ns: int) -> datetime:
    """Convert Apple epoch nanoseconds to datetime (UTC)."""
    unix_ts = apple_ns_to_unix(apple_ns)
    return datetime.fromtimestamp(unix_ts, tz=UTC)


def now_apple_ns() -> int:
    """Get current time as Apple epoch nanoseconds."""
    return datetime_to_apple_ns(datetime.now(UTC))
