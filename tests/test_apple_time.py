from datetime import UTC, datetime

from imessage_data_foundry.utils.apple_time import (
    APPLE_EPOCH_OFFSET,
    NANOSECONDS_PER_SECOND,
    apple_ns_to_datetime,
    apple_ns_to_unix,
    apple_seconds_to_unix,
    datetime_to_apple_ns,
    now_apple_ns,
    unix_to_apple_ns,
    unix_to_apple_seconds,
)


class TestConstants:
    def test_apple_epoch_offset(self):
        assert APPLE_EPOCH_OFFSET == 978307200

    def test_nanoseconds_per_second(self):
        assert NANOSECONDS_PER_SECOND == 1_000_000_000


class TestUnixToAppleSeconds:
    def test_unix_epoch(self):
        result = unix_to_apple_seconds(0)
        assert result == -978307200

    def test_apple_epoch(self):
        result = unix_to_apple_seconds(978307200)
        assert result == 0

    def test_recent_timestamp(self):
        unix_ts = 1704067200.0  # 2024-01-01 00:00:00 UTC
        result = unix_to_apple_seconds(unix_ts)
        assert result == 725760000


class TestAppleSecondsToUnix:
    def test_apple_epoch(self):
        result = apple_seconds_to_unix(0)
        assert result == 978307200.0

    def test_roundtrip(self):
        unix_ts = 1704067200.0
        apple_ts = unix_to_apple_seconds(unix_ts)
        result = apple_seconds_to_unix(apple_ts)
        assert result == unix_ts


class TestUnixToAppleNs:
    def test_apple_epoch(self):
        result = unix_to_apple_ns(978307200.0)
        assert result == 0

    def test_with_fractional_seconds(self):
        result = unix_to_apple_ns(978307200.5)
        assert result == 500_000_000


class TestAppleNsToUnix:
    def test_zero(self):
        result = apple_ns_to_unix(0)
        assert result == 978307200.0

    def test_roundtrip(self):
        unix_ts = 1704067200.5
        apple_ns = unix_to_apple_ns(unix_ts)
        result = apple_ns_to_unix(apple_ns)
        assert abs(result - unix_ts) < 0.000001


class TestDatetimeToAppleNs:
    def test_apple_epoch_datetime(self):
        dt = datetime(2001, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = datetime_to_apple_ns(dt)
        assert result == 0

    def test_naive_datetime_treated_as_utc(self):
        dt_naive = datetime(2001, 1, 1, 0, 0, 0)
        dt_utc = datetime(2001, 1, 1, 0, 0, 0, tzinfo=UTC)
        result_naive = datetime_to_apple_ns(dt_naive)
        result_utc = datetime_to_apple_ns(dt_utc)
        assert result_naive == result_utc


class TestAppleNsToDatetime:
    def test_zero_returns_apple_epoch(self):
        result = apple_ns_to_datetime(0)
        assert result.year == 2001
        assert result.month == 1
        assert result.day == 1
        assert result.tzinfo == UTC

    def test_roundtrip(self):
        dt = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)
        apple_ns = datetime_to_apple_ns(dt)
        result = apple_ns_to_datetime(apple_ns)
        assert result.year == dt.year
        assert result.month == dt.month
        assert result.day == dt.day
        assert result.hour == dt.hour
        assert result.minute == dt.minute
        assert result.second == dt.second


class TestNowAppleNs:
    def test_returns_positive(self):
        result = now_apple_ns()
        assert result > 0

    def test_is_recent(self):
        result = now_apple_ns()
        # Should be after 2020: roughly 600 billion nanoseconds after Apple epoch
        assert result > 600_000_000_000_000_000
