"""Application configuration."""
import os


class Config:
    # The session-signing key MUST now be provided via environment variable.
    # Generate one with:  python -c "import secrets; print(secrets.token_hex(32))"
    # Missing it is a fatal configuration error (checked in app.py).
    SECRET_KEY = os.environ.get("TAX_TRACKER_SECRET")

    # SQLite database file.
    DB_PATH = os.environ.get("TAX_TRACKER_DB", "tax_returns.db")

    # Session cookie hardening (site served over HTTPS behind nginx).
    SESSION_COOKIE_SECURE = True      # browsers only send it over HTTPS
    SESSION_COOKIE_HTTPONLY = True    # JS cannot read the cookie
    SESSION_COOKIE_SAMESITE = "Lax"   # CSRF defense-in-depth alongside tokens
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12  # 12 hours
