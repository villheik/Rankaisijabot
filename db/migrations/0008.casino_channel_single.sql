-- depends: 0007.casino_channels
DROP TABLE casino_allowed_channels;
CREATE TABLE casino_allowed_channels (
    guild_id   INTEGER NOT NULL PRIMARY KEY,
    channel_id INTEGER NOT NULL
);
