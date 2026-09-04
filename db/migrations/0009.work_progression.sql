-- depends: 0006.casino_active_job

CREATE TABLE work_xp (
    user_id  INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    xp       REAL    NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE work_allowed_channels (
    guild_id   INTEGER NOT NULL PRIMARY KEY,
    channel_id INTEGER NOT NULL
);
