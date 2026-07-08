import datetime
import pytest
from bot.cogs.notify import _parse_remind_at

# Fixed "now": 2026-07-08 09:00 UTC = 12:00 EEST (Wednesday)
NOW = datetime.datetime(2026, 7, 8, 9, 0, 0, tzinfo=datetime.timezone.utc).astimezone()
TODAY = NOW.date()
TOMORROW = TODAY + datetime.timedelta(days=1)


def utc(dt: datetime.datetime) -> datetime.datetime:
    return dt.astimezone(datetime.timezone.utc).replace(microsecond=0)


def make_local(date: datetime.date, h: int, m: int) -> datetime.datetime:
    local_tz = NOW.tzinfo
    return datetime.datetime.combine(date, datetime.time(h, m)).replace(tzinfo=local_tz)


class TestTimeOnly:
    def test_future_time_fires_today(self):
        dt, msg = _parse_remind_at(("13:30", "muistuta"), now=NOW)
        assert utc(dt) == utc(make_local(TODAY, 13, 30))
        assert msg == "muistuta"

    def test_past_time_fires_tomorrow(self):
        dt, msg = _parse_remind_at(("11:00", "muistuta"), now=NOW)
        assert utc(dt) == utc(make_local(TOMORROW, 11, 0))

    def test_exact_now_fires_tomorrow(self):
        # 12:00 exactly is not in the future → tomorrow
        dt, _ = _parse_remind_at(("12:00", "x"), now=NOW)
        assert utc(dt) == utc(make_local(TOMORROW, 12, 0))

    def test_multiword_message(self):
        _, msg = _parse_remind_at(("13:30", "osta", "maito"), now=NOW)
        assert msg == "osta maito"


class TestTomorrow:
    def test_tomorrow_basic(self):
        dt, msg = _parse_remind_at(("tomorrow", "09:00", "herätys"), now=NOW)
        assert utc(dt) == utc(make_local(TOMORROW, 9, 0))
        assert msg == "herätys"

    def test_tomorrow_multiword(self):
        _, msg = _parse_remind_at(("tomorrow", "09:00", "osta", "maito"), now=NOW)
        assert msg == "osta maito"

    def test_tomorrow_invalid_time(self):
        assert _parse_remind_at(("tomorrow", "9am", "x"), now=NOW) is None


class TestDate:
    def test_date_without_trailing_dot(self):
        dt, msg = _parse_remind_at(("9.7", "14:00", "teksti"), now=NOW)
        assert utc(dt) == utc(make_local(datetime.date(2026, 7, 9), 14, 0))
        assert msg == "teksti"

    def test_date_with_trailing_dot(self):
        dt, _ = _parse_remind_at(("9.7.", "14:00", "teksti"), now=NOW)
        assert utc(dt) == utc(make_local(datetime.date(2026, 7, 9), 14, 0))

    def test_date_with_explicit_year(self):
        dt, _ = _parse_remind_at(("9.7.2026", "14:00", "teksti"), now=NOW)
        assert utc(dt) == utc(make_local(datetime.date(2026, 7, 9), 14, 0))

    def test_date_multiword_message(self):
        _, msg = _parse_remind_at(("9.7.", "14:00", "osta", "maito"), now=NOW)
        assert msg == "osta maito"


class TestInvalid:
    def test_empty_args(self):
        assert _parse_remind_at((), now=NOW) is None

    def test_only_time_no_message(self):
        assert _parse_remind_at(("13:30",), now=NOW) is None

    def test_only_tomorrow_no_time(self):
        assert _parse_remind_at(("tomorrow",), now=NOW) is None

    def test_only_tomorrow_and_time_no_message(self):
        assert _parse_remind_at(("tomorrow", "13:30"), now=NOW) is None

    def test_invalid_time_format(self):
        assert _parse_remind_at(("13:99", "teksti"), now=NOW) is None

    def test_invalid_date_format(self):
        assert _parse_remind_at(("july9", "14:00", "teksti"), now=NOW) is None

    def test_only_date_no_time_no_message(self):
        assert _parse_remind_at(("9.7.",), now=NOW) is None
