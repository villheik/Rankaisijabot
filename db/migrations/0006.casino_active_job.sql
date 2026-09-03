-- depends: 0005.casino
DROP TABLE IF EXISTS casino_job_cooldowns;

CREATE TABLE casino_active_job (
    user_id     INTEGER NOT NULL,
    guild_id    INTEGER NOT NULL,
    job         TEXT NOT NULL,
    finishes_at TEXT NOT NULL,
    PRIMARY KEY (user_id, guild_id)
);
