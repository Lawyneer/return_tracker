"""SQLite connection handling and schema initialization."""
import sqlite3
from flask import g
from config import Config
from constants import STATUSES


def get_db():
    """Return the database connection for this request (created lazily
    and stored on Flask's application-context `g` so it's reused within
    a request and closed afterwards)."""
    if "db" not in g:
        g.db = sqlite3.connect(Config.DB_PATH)
        g.db.row_factory = sqlite3.Row          # rows behave like dicts
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exc=None):
    """Close the connection at the end of the request
    (registered as a teardown hook by the app factory)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables/indexes if missing and seed the statuses table.

    Safe to call on every startup: uses CREATE TABLE IF NOT EXISTS and
    INSERT OR IGNORE, so existing data is never touched.
    """
    db = sqlite3.connect(Config.DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT NOT NULL UNIQUE,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS statuses (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        code        TEXT NOT NULL UNIQUE,
        label       TEXT NOT NULL,
        stage_order INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tax_returns (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        return_name        TEXT NOT NULL,
        tax_year           INTEGER NOT NULL,
        return_type        TEXT NOT NULL,
        due_date           TEXT,
        extended_due_date  TEXT,
        archived_at        TIMESTAMP,
        current_status_id  INTEGER NOT NULL REFERENCES statuses(id),
        created_by         INTEGER NOT NULL REFERENCES users(id),
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (return_name, tax_year, return_type)
    );
    CREATE TABLE IF NOT EXISTS status_history (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        return_id     INTEGER NOT NULL REFERENCES tax_returns(id) ON DELETE CASCADE,
        old_status_id INTEGER REFERENCES statuses(id),
        new_status_id INTEGER NOT NULL REFERENCES statuses(id),
        changed_by    INTEGER NOT NULL REFERENCES users(id),
        changed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        note          TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_hist_return ON status_history(return_id, changed_at);
    CREATE INDEX IF NOT EXISTS idx_returns_status ON tax_returns(current_status_id);
    """)
    # Migration for databases created before archiving existed.
    cols = [r["name"] for r in db.execute("PRAGMA table_info(tax_returns)").fetchall()]
    if "archived_at" not in cols:
        db.execute("ALTER TABLE tax_returns ADD COLUMN archived_at TIMESTAMP")
    # Seed the fixed workflow statuses (no-op if they already exist).
    for code, label, order in STATUSES:
        db.execute("INSERT OR IGNORE INTO statuses (code, label, stage_order) VALUES (?,?,?)",
                   (code, label, order))
    db.commit()
    db.close()