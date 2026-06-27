import datetime
import pytest
from bot.cogs.f1 import _parse_dt, _parse_sessions, _format_session, _next_race

RACE_NORMAL = {
    "raceName": "Test Grand Prix",
    "round": "5",
    "season": "2025",
    "Circuit": {"circuitName": "Test Circuit", "Location": {"country": "Finland"}},
    "date": "2025-08-03",
    "time": "13:00:00Z",
    "FirstPractice": {"date": "2025-08-01", "time": "10:30:00Z"},
    "SecondPractice": {"date": "2025-08-01", "time": "14:00:00Z"},
    "ThirdPractice": {"date": "2025-08-02", "time": "10:30:00Z"},
    "Qualifying": {"date": "2025-08-02", "time": "14:00:00Z"},
}

RACE_SPRINT = {
    "raceName": "Sprint Grand Prix",
    "round": "6",
    "season": "2025",
    "Circuit": {"circuitName": "Sprint Circuit", "Location": {"country": "Belgium"}},
    "date": "2025-09-07",
    "time": "13:00:00Z",
    "FirstPractice": {"date": "2025-09-05", "time": "10:30:00Z"},
    "SprintShootout": {"date": "2025-09-06", "time": "10:30:00Z"},
    "Sprint": {"date": "2025-09-06", "time": "14:30:00Z"},
    "Qualifying": {"date": "2025-09-07", "time": "10:00:00Z"},
}


class TestParseDt:
    def test_parses_utc(self):
        dt = _parse_dt("2025-08-03", "13:00:00Z")
        assert dt.tzinfo == datetime.timezone.utc
        assert dt.year == 2025
        assert dt.month == 8
        assert dt.day == 3
        assert dt.hour == 13


class TestParseSessions:
    def test_normal_weekend_order(self):
        sessions = _parse_sessions(RACE_NORMAL)
        keys = [k for k, _ in sessions]
        assert keys == ["FirstPractice", "SecondPractice", "ThirdPractice", "Qualifying", "Race"]

    def test_sprint_weekend_order(self):
        sessions = _parse_sessions(RACE_SPRINT)
        keys = [k for k, _ in sessions]
        assert keys == ["FirstPractice", "SprintShootout", "Sprint", "Qualifying", "Race"]

    def test_race_always_last(self):
        sessions = _parse_sessions(RACE_NORMAL)
        assert sessions[-1][0] == "Race"


class TestFormatSession:
    def test_contains_session_name(self):
        dt = _parse_dt("2025-08-02", "14:00:00Z")
        result = _format_session("Qualifying", dt)
        assert "Aika-ajot" in result

    def test_contains_time(self):
        dt = datetime.datetime(2025, 8, 2, 14, 0, tzinfo=datetime.timezone.utc)
        result = _format_session("Race", dt)
        assert "Kilpailu" in result


class TestNextRace:
    def test_returns_none_when_all_past(self):
        now = datetime.datetime(2025, 9, 8, 0, 0, tzinfo=datetime.timezone.utc)
        assert _next_race([RACE_NORMAL, RACE_SPRINT], now) is None

    def test_returns_first_upcoming(self):
        now = datetime.datetime(2025, 8, 1, 0, 0, tzinfo=datetime.timezone.utc)
        race, remaining = _next_race([RACE_NORMAL, RACE_SPRINT], now)
        assert race["raceName"] == "Test Grand Prix"

    def test_skips_finished_race(self):
        now = datetime.datetime(2025, 8, 4, 0, 0, tzinfo=datetime.timezone.utc)
        race, remaining = _next_race([RACE_NORMAL, RACE_SPRINT], now)
        assert race["raceName"] == "Sprint Grand Prix"

    def test_remaining_filters_past_sessions(self):
        now = datetime.datetime(2025, 8, 2, 12, 0, tzinfo=datetime.timezone.utc)
        race, remaining = _next_race([RACE_NORMAL], now)
        keys = [k for k, _ in remaining]
        assert "FirstPractice" not in keys
        assert "SecondPractice" not in keys
        assert "ThirdPractice" not in keys
        assert "Qualifying" in keys
        assert "Race" in keys
