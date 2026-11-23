"""SQLite database setup and connection helpers."""

import sqlite3
from pathlib import Path

"""
Initialize the SQLite database.
This module provides functions to create the database schema and establish a connection to the SQLite database. It ensures that the necessary tables and indexes are created if they do not already exist.

Functions:
- db(db_path: Path): Returns a SQLite connection with row access by column name.
- initialize(db_path: Path): Creates database tables and indexes if they do not exist.
"""

SCHEMA = """
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    occurred_on TEXT NOT NULL,
    description TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    category TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('expense','income')),
    source TEXT NOT NULL,
    import_key TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, import_key)
);

CREATE TABLE IF NOT EXISTS recurring_rules (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    category TEXT NOT NULL,
    kind TEXT NOT NULL,
    day_of_month INTEGER NOT NULL CHECK(day_of_month BETWEEN 1 AND 28),
    next_due TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_date
ON transactions(user_id, occurred_on);
"""


def db(db_path: Path):
    """
    Return a SQLite connection with row access by column name.

    :param db_path: Path to the SQLite database file
    :return: SQLite connection
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def initialize(db_path: Path) -> None:
    """
    Create database tables and indexes if they do not exist.

    :param db_path: Path to the SQLite database file
    """
    with db(db_path) as con:
        con.executescript(SCHEMA)
