import sqlite3
import pytest
from unittest.mock import MagicMock
from bot.cogs.markov import Markov

CHANNEL = 111
OTHER_CHANNEL = 222

MESSAGES = [
    (1,  1, "alice", "the cat sat on the mat",                          CHANNEL),
    (2,  1, "alice", "the dog ran in the park",                         CHANNEL),
    (3,  1, "alice", "cats and dogs are great pets",                    CHANNEL),
    (4,  1, "alice", "the quick brown fox jumps over the lazy dog",     CHANNEL),
    (5,  1, "alice", "a stitch in time saves nine",                     CHANNEL),
    (6,  1, "alice", "the early bird catches the worm",                 CHANNEL),
    (7,  1, "alice", "all that glitters is not gold",                   CHANNEL),
    (8,  1, "alice", "actions speak louder than words",                 CHANNEL),
    (9,  1, "alice", "better late than never is a common saying",       CHANNEL),
    (10, 1, "alice", "the pen is mightier than the sword indeed",       CHANNEL),
    (11, 2, "bob",   "hello world",                                     CHANNEL),
    (12, 2, "bob",   "bye world",                                       CHANNEL),
]

NICKNAMES = [
    (CHANNEL, "al",       "alice"),
    (CHANNEL, "combined", "alice"),
    (CHANNEL, "combined", "bob"),
]


@pytest.fixture
def db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("bot.cogs.markov.DB_PATH", db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY, user_id INTEGER,
            username TEXT, content TEXT, channel_id INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE nicknames (
            channel_id INTEGER, nickname TEXT, username TEXT,
            PRIMARY KEY (channel_id, nickname, username)
        )
    """)
    conn.executemany("INSERT INTO messages VALUES (?, ?, ?, ?, ?)", MESSAGES)
    conn.executemany("INSERT INTO nicknames VALUES (?, ?, ?)", NICKNAMES)
    conn.commit()
    conn.close()
    yield


@pytest.fixture
def cog(db, monkeypatch):
    monkeypatch.setattr(Markov, "nightly_rebuild", MagicMock())
    return Markov(bot=None)


class TestResolveUsernames:
    def test_no_nickname_returns_target(self, cog):
        assert cog._resolve_usernames("alice", CHANNEL) == ["alice"]

    def test_nickname_resolves_to_username(self, cog):
        assert cog._resolve_usernames("al", CHANNEL) == ["alice"]

    def test_nickname_case_insensitive(self, cog):
        assert cog._resolve_usernames("AL", CHANNEL) == ["alice"]

    def test_nickname_multiple_usernames(self, cog):
        assert set(cog._resolve_usernames("combined", CHANNEL)) == {"alice", "bob"}

    def test_unknown_target_returns_itself(self, cog):
        assert cog._resolve_usernames("nobody", CHANNEL) == ["nobody"]

    def test_nickname_not_shared_across_channels(self, cog):
        assert cog._resolve_usernames("al", OTHER_CHANNEL) == ["al"]


class TestBuildModel:
    def test_builds_model_with_enough_messages(self, cog):
        model, count = cog._build_model(CHANNEL, ["alice"])
        assert model is not None
        assert count == 10

    def test_returns_none_with_too_few_messages(self, cog):
        model, count = cog._build_model(CHANNEL, ["bob"])
        assert model is None
        assert count == 2

    def test_returns_none_for_unknown_user(self, cog):
        model, count = cog._build_model(CHANNEL, ["nobody"])
        assert model is None
        assert count == 0

    def test_returns_none_wrong_channel(self, cog):
        model, count = cog._build_model(OTHER_CHANNEL, ["alice"])
        assert model is None

    def test_combined_usernames_pools_messages(self, cog):
        model, count = cog._build_model(CHANNEL, ["alice", "bob"])
        assert model is not None
        assert count == 12

    def test_state_size_small_corpus(self, cog):
        model, _ = cog._build_model(CHANNEL, ["alice"])
        assert model.state_size == 1

    def test_model_can_generate_sentence(self, cog):
        model, _ = cog._build_model(CHANNEL, ["alice"])
        assert model.make_sentence(tries=100) is not None
