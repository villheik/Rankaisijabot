-- depends: 0004.notify
CREATE TABLE casino_balance (
    user_id          INTEGER NOT NULL,
    guild_id         INTEGER NOT NULL,
    balance          INTEGER NOT NULL DEFAULT 1000,
    debt             INTEGER NOT NULL DEFAULT 0,
    pending_winnings INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE casino_job_cooldowns (
    user_id   INTEGER NOT NULL,
    guild_id  INTEGER NOT NULL,
    job       TEXT NOT NULL,
    last_used TEXT NOT NULL,
    PRIMARY KEY (user_id, guild_id, job)
);
