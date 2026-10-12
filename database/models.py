"""
database/models.py
SQLite database uchun jadval sxemalari (SQL DDL).
"""

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    full_name TEXT,
    coins INTEGER DEFAULT 0,
    vip INTEGER DEFAULT 0,
    vip_expire_at TEXT,
    referral_id INTEGER,
    referral_count INTEGER DEFAULT 0,
    referral_rewarded INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
"""

CREATE_DOWNLOADS_TABLE = """
CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    url TEXT,
    date TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
);
"""

CREATE_PAYMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    date TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
);
"""

CREATE_DAILY_USAGE_TABLE = """
CREATE TABLE IF NOT EXISTS daily_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    count INTEGER DEFAULT 0,
    UNIQUE(user_id, date),
    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
);
"""

ALL_TABLES = [
    CREATE_USERS_TABLE,
    CREATE_DOWNLOADS_TABLE,
    CREATE_PAYMENTS_TABLE,
    CREATE_DAILY_USAGE_TABLE,
]
