-- depends: 0001.initial
CREATE TABLE IF NOT EXISTS f1_announced (
    season INTEGER,
    round INTEGER,
    session TEXT,
    PRIMARY KEY (season, round, session)
);

CREATE TABLE IF NOT EXISTS f1_subscribers (
    user_id INTEGER PRIMARY KEY
);
