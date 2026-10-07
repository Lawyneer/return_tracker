"""Application configuration."""
import os


class Config:
    # Flask session-signing key. In production this should come from an
    # environment variable or secret manager instead of being generated here.
    SECRET_KEY = os.environ.get("TAX_TRACKER_SECRET", os.urandom(24))

    # SQLite database file (kept relative so the existing tax_returns.db
    # keeps working if run from the same directory).
    DB_PATH = os.environ.get("TAX_TRACKER_DB", "tax_returns.db")