-- depends:
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    username TEXT,
    content TEXT,
    channel_id INTEGER
);

CREATE TABLE meta (
    channel_id INTEGER PRIMARY KEY,
    last_message_id INTEGER
);

CREATE TABLE nicknames (
    channel_id INTEGER,
    nickname TEXT,
    username TEXT,
    PRIMARY KEY (channel_id, nickname, username)
);
