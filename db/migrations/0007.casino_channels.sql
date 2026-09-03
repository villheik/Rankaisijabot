-- depends: 0006.casino_active_job
CREATE TABLE casino_allowed_channels (
    guild_id   INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    PRIMARY KEY (guild_id, channel_id)
);
