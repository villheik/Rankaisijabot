import datetime
import pytest
from bot.cogs.random_msg import RandomMsg, _snowflake_to_dt, _format_dt
from tests.conftest import CHANNEL, ALICE_ID, BOB_ID


@pytest.fixture
def cog():
    return RandomMsg(bot=None)


class TestTimestamp:
    def test_snowflake_to_dt_is_timezone_aware(self):
        snowflake = 1234567890 << 22
        dt = _snowflake_to_dt(snowflake)
        assert dt.tzinfo is not None

    def test_format_dt_includes_timezone(self):
        dt = datetime.datetime(2025, 5, 1, 20, 56, tzinfo=datetime.timezone.utc).astimezone()
        result = _format_dt(dt)
        tz = dt.strftime('%Z')
        assert tz in result
        assert "()" not in result


class TestBuildRegex:
    def test_exact_word_matches(self):
        p = RandomMsg._build_regex("dragon")
        assert p.search("the dragon sleeps")

    def test_exact_word_no_prefix(self):
        p = RandomMsg._build_regex("dragon")
        assert not p.search("firedragon appeared")

    def test_exact_word_no_suffix(self):
        p = RandomMsg._build_regex("dragon")
        assert not p.search("dragonfly is an insect")

    def test_trailing_wildcard_matches_suffix(self):
        p = RandomMsg._build_regex("dragon*")
        assert p.search("dragonfly is an insect")

    def test_trailing_wildcard_no_prefix(self):
        p = RandomMsg._build_regex("dragon*")
        assert not p.search("a firedragon appeared")

    def test_leading_wildcard_matches_prefix(self):
        p = RandomMsg._build_regex("*dragon")
        assert p.search("a firedragon appeared")

    def test_leading_wildcard_no_suffix(self):
        p = RandomMsg._build_regex("*dragon")
        assert not p.search("dragonfly is an insect")

    def test_both_wildcards_matches_all(self):
        p = RandomMsg._build_regex("*dragon*")
        assert p.search("the dragon sleeps")
        assert p.search("dragonfly is an insect")
        assert p.search("a firedragon appeared")
        assert p.search("firedragonfly exists")

    def test_middle_wildcard_matches(self):
        p = RandomMsg._build_regex("dra*on")
        assert p.search("the dragon sleeps")

    def test_middle_wildcard_no_suffix(self):
        p = RandomMsg._build_regex("dra*on")
        assert not p.search("dragonfly is an insect")

    def test_case_insensitive(self):
        p = RandomMsg._build_regex("Dragon")
        assert p.search("the dragon sleeps")

    def test_discord_emoji(self):
        p = RandomMsg._build_regex("<:smile:111222333444>")
        assert p.search("haha <:smile:111222333444> lol")
        assert not p.search("nothing here")

    def test_discord_mention_format(self):
        p = RandomMsg._build_regex("<@999888777>")
        assert p.search("hey <@999888777> check this")
        assert not p.search("nothing here")


class TestFetchRandom:
    def test_no_term_returns_row(self, db, cog):
        result = cog._fetch_random(CHANNEL)
        assert result is not None

    def test_exact_word(self, db, cog):
        result = cog._fetch_random(CHANNEL, "dragon")
        assert result is not None
        content, _, _ = result
        assert content == "the dragon sleeps"

    def test_trailing_wildcard(self, db, cog):
        result = cog._fetch_random(CHANNEL, "dragon*")
        assert result is not None
        content, _, _ = result
        assert content in {"the dragon sleeps", "dragonfly is an insect"}

    def test_leading_wildcard(self, db, cog):
        result = cog._fetch_random(CHANNEL, "*dragon")
        assert result is not None
        content, _, _ = result
        assert content in {"the dragon sleeps", "a firedragon appeared"}

    def test_both_wildcards(self, db, cog):
        result = cog._fetch_random(CHANNEL, "*dragon*")
        assert result is not None
        content, _, _ = result
        assert content in {
            "the dragon sleeps",
            "dragonfly is an insect",
            "a firedragon appeared",
            "firedragonfly exists",
        }

    def test_no_results(self, db, cog):
        result = cog._fetch_random(CHANNEL, "unicorn")
        assert result is None

    def test_nickname_shown(self, db, cog):
        result = cog._fetch_random(CHANNEL, "dragon")
        assert result is not None
        _, display_name, _ = result
        assert display_name == "ally"

    def test_no_nickname_uses_username(self, db, cog):
        result = cog._fetch_random(CHANNEL, "nothing relevant")
        assert result is not None
        _, display_name, _ = result
        assert display_name == "bob"

    def test_mention_search(self, db, cog):
        result = cog._fetch_random(CHANNEL, "@alice")
        assert result is not None
        content, _, _ = result
        assert "@alice" in content
        assert f"<@{ALICE_ID}>" not in content

    def test_mention_via_nickname(self, db, cog):
        result = cog._fetch_random(CHANNEL, "@ally")
        assert result is not None
        content, _, _ = result
        assert "@alice" in content
        assert f"<@{ALICE_ID}>" not in content

    def test_mention_unknown_user(self, db, cog):
        result = cog._fetch_random(CHANNEL, "@nobody")
        assert result is None

    def test_timestamp_returned(self, db, cog):
        result = cog._fetch_random(CHANNEL, "dragon")
        assert result is not None
        _, _, timestamp = result
        assert isinstance(timestamp, str)
        assert "klo" in timestamp

    def test_bot_commands_excluded_by_search(self, db, cog):
        # "secretword" exists only in "!random secretword" — should not be found
        result = cog._fetch_random(CHANNEL, "secretword")
        assert result is None

    def test_bot_commands_excluded_no_term(self, db, cog):
        for _ in range(30):
            result = cog._fetch_random(CHANNEL)
            assert result is not None
            content, _, _ = result
            assert not content.startswith("!")
