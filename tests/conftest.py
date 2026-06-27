import sqlite3
import pytest

CHANNEL = 999
ALICE_ID = 111
BOB_ID = 222

MESSAGES = [
    (1, ALICE_ID, "alice", "the dragon sleeps",                  CHANNEL),
    (2, ALICE_ID, "alice", "dragonfly is an insect",             CHANNEL),
    (3, BOB_ID,   "bob",   "a firedragon appeared",              CHANNEL),
    (4, BOB_ID,   "bob",   "firedragonfly exists",               CHANNEL),
    (5, BOB_ID,   "bob",   "nothing relevant here",              CHANNEL),
    (6, BOB_ID,   "bob",   f"hey <@{ALICE_ID}> check this out",  CHANNEL),
    (7, ALICE_ID, "alice", f"<@{BOB_ID}> is that you",           CHANNEL),
    (8, BOB_ID,   "bob",   "!random secretword",                 CHANNEL),
    (9, BOB_ID,   "bob",   "!poe witch minion",                  CHANNEL),
]

NICKNAMES = [
    (CHANNEL, "ally", "alice"),
]


@pytest.fixture
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("bot.cogs.random_msg.DB_PATH", str(db_path))

    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            username TEXT,
            content TEXT,
            channel_id INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE nicknames (
            channel_id INTEGER,
            nickname TEXT,
            username TEXT,
            PRIMARY KEY (channel_id, nickname, username)
        )
    """)
    conn.executemany("INSERT INTO messages VALUES (?, ?, ?, ?, ?)", MESSAGES)
    conn.executemany("INSERT INTO nicknames VALUES (?, ?, ?)", NICKNAMES)
    conn.commit()
    conn.close()
    yield
