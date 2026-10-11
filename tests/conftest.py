"""Shared pytest fixtures: throwaway database, test client, logged-in user."""
import pytest
from config import Config


@pytest.fixture()
def app(tmp_path, monkeypatch):
    """Fresh app with an isolated, per-test SQLite database."""
    monkeypatch.setattr(Config, "DB_PATH", str(tmp_path / "test_tax_returns.db"))
    from app import create_app

    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret-key"

    application = create_app(TestConfig)
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    """Direct database access for asserting on rows."""
    from db import get_db
    with app.app_context():
        yield get_db()


def status_id(db, code):
    """Look up a status id by its code (e.g. 'not_started')."""
    return db.execute("SELECT id FROM statuses WHERE code = ?", (code,)).fetchone()["id"]


@pytest.fixture()
def alice(app, client, db):
    """Create user 'Alice' and log the client in as her; returns her user id."""
    client.post("/login",
                data={"action": "add_user", "new_username": "Alice"},
                follow_redirects=True)
    row = db.execute("SELECT id FROM users WHERE username = 'Alice'").fetchone()
    client.post("/login",
                data={"action": "login", "user_id": str(row["id"])},
                follow_redirects=True)
    return row["id"]


def add_return(client, name="Acme Corp", year="2026", rtype="1120",
               due="2026-04-15", ext="", noteless=False):
    """Helper: create a return through the web form, return the response."""
    return client.post("/returns/new",
                       data={"return_name": name, "tax_year": year,
                             "return_type": rtype, "due_date": due,
                             "extended_due_date": ext},
                       follow_redirects=True)


def return_id(db, name="Acme Corp"):
    return db.execute("SELECT id FROM tax_returns WHERE return_name = ?",
                      (name,)).fetchone()["id"]