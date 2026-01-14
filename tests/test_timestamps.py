"""Tests for timestamp generation."""

import random
from datetime import UTC, datetime, timedelta

import pytest

from imessage_data_foundry.conversations.timestamps import (
    CIRCADIAN_WEIGHTS,
    RESPONSE_TIME_RANGES,
    TimestampConfig,
    _generate_scattered_timestamps,
    _generate_single_session,
    _get_circadian_weight,
    _pick_weighted_time,
    _plan_sessions,
    generate_timestamps,
    get_response_delay,
)
from imessage_data_foundry.personas.models import Persona, ResponseTime
from imessage_data_foundry.utils.apple_time import apple_ns_to_datetime


def make_persona(
    name: str = "Test",
    response_time: ResponseTime = ResponseTime.MINUTES,
    is_self: bool = False,
) -> Persona:
    return Persona(
        name=name,
        identifier="+15551234567",
        typical_response_time=response_time,
        is_self=is_self,
    )


class TestGenerateTimestamps:
    def test_returns_correct_count(self):
        start = datetime(2024, 1, 1, 8, 0, tzinfo=UTC)
        end = datetime(2024, 1, 7, 22, 0, tzinfo=UTC)
        personas = [make_persona("Alice"), make_persona("Bob", is_self=True)]

        result = generate_timestamps(start, end, 100, personas, seed=42)

        assert len(result) == 100

    def test_all_within_range(self):
        start = datetime(2024, 1, 1, 8, 0, tzinfo=UTC)
        end = datetime(2024, 1, 7, 22, 0, tzinfo=UTC)
        personas = [make_persona(), make_persona(is_self=True)]

        result = generate_timestamps(start, end, 50, personas, seed=42)

        for ts in result:
            dt = apple_ns_to_datetime(ts)
            assert start <= dt <= end

    def test_chronologically_sorted(self):
        start = datetime(2024, 1, 1, 8, 0, tzinfo=UTC)
        end = datetime(2024, 1, 7, 22, 0, tzinfo=UTC)
        personas = [make_persona(), make_persona(is_self=True)]

        result = generate_timestamps(start, end, 100, personas, seed=42)

        for i in range(1, len(result)):
            assert result[i] >= result[i - 1]

    def test_deterministic_with_seed(self):
        start = datetime(2024, 1, 1, 8, 0, tzinfo=UTC)
        end = datetime(2024, 1, 7, 22, 0, tzinfo=UTC)
        personas = [make_persona(), make_persona(is_self=True)]

        result1 = generate_timestamps(start, end, 50, personas, seed=123)
        result2 = generate_timestamps(start, end, 50, personas, seed=123)

        assert result1 == result2

    def test_different_seeds_different_results(self):
        start = datetime(2024, 1, 1, 8, 0, tzinfo=UTC)
        end = datetime(2024, 1, 7, 22, 0, tzinfo=UTC)
        personas = [make_persona(), make_persona(is_self=True)]

        result1 = generate_timestamps(start, end, 50, personas, seed=123)
        result2 = generate_timestamps(start, end, 50, personas, seed=456)

        assert result1 != result2

    def test_empty_count(self):
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 2, tzinfo=UTC)

        result = generate_timestamps(start, end, 0, [])

        assert result == []

    def test_invalid_time_range(self):
        start = datetime(2024, 1, 2, tzinfo=UTC)
        end = datetime(2024, 1, 1, tzinfo=UTC)

        with pytest.raises(ValueError, match="end must be after start"):
            generate_timestamps(start, end, 10, [])

    def test_time_range_too_short(self):
        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 1, 0, 0, 10, tzinfo=UTC)

        with pytest.raises(ValueError, match="Time range too short"):
            generate_timestamps(start, end, 100, [])

    def test_small_count_no_sessions(self):
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 2, tzinfo=UTC)
        personas = [make_persona(), make_persona(is_self=True)]

        result = generate_timestamps(start, end, 3, personas, seed=42)

        assert len(result) == 3


class TestPlanSessions:
    def test_respects_session_ratio(self):
        rng = random.Random(42)
        config = TimestampConfig()

        sessions = _plan_sessions(100, config, rng)

        total_in_sessions = sum(s.size for s in sessions)
        assert 60 <= total_in_sessions <= 80

    def test_session_sizes_in_range(self):
        rng = random.Random(42)
        config = TimestampConfig()

        sessions = _plan_sessions(200, config, rng)

        for session in sessions:
            assert config.min_session_size <= session.size <= config.max_session_size

    def test_no_sessions_for_small_count(self):
        rng = random.Random(42)
        config = TimestampConfig()

        sessions = _plan_sessions(3, config, rng)

        assert sessions == []


class TestGenerateSingleSession:
    def test_returns_correct_count(self):
        rng = random.Random(42)
        start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        personas = [make_persona(), make_persona(is_self=True)]
        config = TimestampConfig()

        result = _generate_single_session(start, 10, personas, config, rng)

        assert len(result) == 10

    def test_timestamps_increase(self):
        rng = random.Random(42)
        start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        personas = [make_persona(), make_persona(is_self=True)]
        config = TimestampConfig()

        result = _generate_single_session(start, 10, personas, config, rng)

        for i in range(1, len(result)):
            assert result[i] > result[i - 1]

    def test_first_timestamp_is_start(self):
        rng = random.Random(42)
        start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        config = TimestampConfig()

        result = _generate_single_session(start, 5, [], config, rng)

        assert result[0] == start


class TestGenerateScatteredTimestamps:
    def test_returns_correct_count(self):
        rng = random.Random(42)
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 7, tzinfo=UTC)

        result = _generate_scattered_timestamps(start, end, 20, rng)

        assert len(result) == 20

    def test_all_within_range(self):
        rng = random.Random(42)
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 1, 7, tzinfo=UTC)

        result = _generate_scattered_timestamps(start, end, 50, rng)

        for ts in result:
            assert start <= ts <= end


class TestCircadianWeight:
    def test_peak_evening_hours(self):
        weight = _get_circadian_weight(19)
        assert weight == 1.0

    def test_minimum_night_hours(self):
        weight = _get_circadian_weight(3)
        assert weight == 0.05

    def test_morning_weight(self):
        weight = _get_circadian_weight(8)
        assert weight == 0.70

    def test_all_hours_have_weight(self):
        for hour in range(24):
            weight = _get_circadian_weight(hour)
            assert 0 < weight <= 1.0


class TestPickWeightedTime:
    def test_returns_time_in_range(self):
        rng = random.Random(42)
        start = datetime(2024, 1, 1, 18, 0, tzinfo=UTC)
        end = datetime(2024, 1, 1, 21, 0, tzinfo=UTC)

        result = _pick_weighted_time(start, end, rng)

        assert start <= result <= end

    def test_favors_high_weight_hours(self):
        start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 2, 0, 0, tzinfo=UTC)

        evening_count = 0
        night_count = 0
        iterations = 500

        for i in range(iterations):
            result = _pick_weighted_time(start, end, random.Random(i))
            hour = result.hour
            if 18 <= hour < 21:
                evening_count += 1
            elif 0 <= hour < 6:
                night_count += 1

        assert evening_count > night_count


class TestGetResponseDelay:
    def test_instant_responder(self):
        persona = make_persona(response_time=ResponseTime.INSTANT)
        rng = random.Random(42)

        delay = get_response_delay(persona, rng)

        assert timedelta(seconds=4) <= delay <= timedelta(seconds=75)

    def test_minutes_responder(self):
        persona = make_persona(response_time=ResponseTime.MINUTES)
        rng = random.Random(42)

        delay = get_response_delay(persona, rng)

        assert timedelta(seconds=48) <= delay <= timedelta(seconds=720)

    def test_hours_responder(self):
        persona = make_persona(response_time=ResponseTime.HOURS)
        rng = random.Random(42)

        delay = get_response_delay(persona, rng)

        assert timedelta(minutes=24) <= delay <= timedelta(hours=5)

    def test_days_responder(self):
        persona = make_persona(response_time=ResponseTime.DAYS)
        rng = random.Random(42)

        delay = get_response_delay(persona, rng)

        assert timedelta(hours=9) <= delay <= timedelta(days=3)

    def test_deterministic_with_seed(self):
        persona = make_persona(response_time=ResponseTime.MINUTES)

        delay1 = get_response_delay(persona, random.Random(42))
        delay2 = get_response_delay(persona, random.Random(42))

        assert delay1 == delay2


class TestResponseTimeRanges:
    def test_all_response_times_have_ranges(self):
        for rt in ResponseTime:
            assert rt in RESPONSE_TIME_RANGES

    def test_ranges_are_valid(self):
        for _rt, (min_s, max_s) in RESPONSE_TIME_RANGES.items():
            assert min_s > 0
            assert max_s > min_s


class TestCircadianWeights:
    def test_covers_all_hours(self):
        covered = set()
        for start, end, _ in CIRCADIAN_WEIGHTS:
            for hour in range(start, end):
                covered.add(hour)

        assert covered == set(range(24))

    def test_weights_are_valid(self):
        for _, _, weight in CIRCADIAN_WEIGHTS:
            assert 0 < weight <= 1.0
