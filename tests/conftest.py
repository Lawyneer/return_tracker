"""Shared pytest fixtures: throwaway database, test client, logged-in user."""
import pytest
from config import Config

# A password satisfying the full policy (20+ chars, lower, upper, digit,
# ASCII special). Used to provision test users directly in the database.
VALID_PASSWORD = "Correct-Horse-Battery-42!"


@pytest.fixture()
def app(tmp_path, monkeypatch):
    """Fresh app with an isolated, per-test SQLite database."""
    monkeypatch.setattr(Config, "DB_PATH", str(tmp_path / "test_tax_returns.db"))
    from app import create_app

    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret-key"        # create_app refuses to boot without one
        WTF_CSRF_ENABLED = False              # forms in tests don't carry tokens
        SESSION_COOKIE_SECURE = False         # test client speaks plain HTTP

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


def create_user(db, username="Alice", password=VALID_PASSWORD):
    """Insert a user with a properly hashed password; return the id."""
    from security import hash_password
    db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
               (username, hash_password(password)))
    db.commit()
    return db.execute("SELECT id FROM users WHERE username = ?",
                      (username,)).fetchone()["id"]


def login(client, username="Alice", password=VALID_PASSWORD):
    """Log the test client in as the given user; returns the response."""
    return client.post("/login",
                       data={"username": username, "password": password},
                       follow_redirects=True)


def status_id(db, code):
    """Look up a status id by its code (e.g. 'not_started')."""
    return db.execute("SELECT id FROM statuses WHERE code = ?", (code,)).fetchone()["id"]


@pytest.fixture()
def alice(app, client, db):
    """Create user 'Alice' (with a compliant password) and log the client
    in as her; returns her user id."""
    uid = create_user(db, "Alice")
    response = login(client)
    assert response.status_code == 200
    return uid


def add_return(client, name="Acme Corp", year="2026", rtype="1120",
               due="2026-04-15", ext="", signer=""):
    """Helper: create a return through the web form, return the response."""
    return client.post("/returns/new",
                       data={"return_name": name, "tax_year": year,
                             "return_type": rtype, "due_date": due,
                             "extended_due_date": ext, "signer": signer},
                       follow_redirects=True)


def return_id(db, name="Acme Corp"):
    return db.execute("SELECT id FROM tax_returns WHERE return_name = ?",
                      (name,)).fetchone()["id"]
