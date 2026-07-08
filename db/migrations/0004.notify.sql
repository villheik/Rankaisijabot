-- depends: 0003.release_config
CREATE TABLE notify_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    remind_at TEXT NOT NULL,
    message TEXT NOT NULL
);
