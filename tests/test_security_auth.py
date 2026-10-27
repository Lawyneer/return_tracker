"""Security refactor: password policy, username policy, argon2 hashing,
login/logout behavior, brute-force lockouts, CSRF enforcement, and the
production session-cookie hardening flags."""
import pytest

from config import Config
from tests.conftest import (VALID_PASSWORD, create_user, login,
                             status_id, add_return, return_id)

BAD_PASSWORD = "wrong-wrong-wrong-wrong-1!"   # policy-compliant but wrong


# ---------------------------- password policy --------------------------------

def test_password_minimum_length():
    from security import validate_password, ValidationError
    pw = "Short1!" * 2  # 14 chars — too short
    with pytest.raises(ValidationError):
        validate_password(pw)


def test_password_maximum_length():
    from security import validate_password, ValidationError
    with pytest.raises(ValidationError):
        validate_password("Aa1!" + "x" * 97)   # 101 chars — over the cap


def test_password_at_exact_limits():
    from security import validate_password
    assert validate_password("Aa1!" + "b" * 16)            # exactly 20
    assert validate_password("Aa1!" + "b" * 96)            # exactly 100


def test_password_requires_lowercase():
    from security import validate_password, ValidationError
    with pytest.raises(ValidationError):
        validate_password("UPPER-ONLY-PASSWORD-1!")


def test_password_requires_uppercase():
    from security import validate_password, ValidationError
    with pytest.raises(ValidationError):
        validate_password("lower-only-password-1!")


def test_password_requires_digit():
    from security import validate_password, ValidationError
    with pytest.raises(ValidationError):
        validate_password("no-digit-password-A!")


def test_password_requires_ascii_special():
    from security import validate_password, ValidationError
    with pytest.raises(ValidationError):
        validate_password("noSpecialCharsAtAll1A" + "x")  # 21 chars, letters/digits only


def test_password_rejects_unicode_special_only():
    from security import validate_password, ValidationError
    with pytest.raises(ValidationError):
        validate_password("unicodeOnlyÉàü1Apassword" + "x")  # non-ASCII specials only


def test_valid_password_accepted():
    from security import validate_password
    assert validate_password(VALID_PASSWORD) == VALID_PASSWORD


# ---------------------------- username policy --------------------------------

def test_username_accepts_email():
    from security import validate_username
    assert validate_username("jane@example.com") == "jane@example.com"


def test_username_accepts_alphanumeric():
    from security import validate_username
    assert validate_username("jb_chen_42") == "jb_chen_42"


def test_username_rejects_bad_chars():
    from security import validate_username, ValidationError
    for bad in ("has space", "no!/slashes", "a" * 300):
        with pytest.raises(ValidationError):
            validate_username(bad)


def test_username_rejects_empty():
    from security import validate_username, ValidationError
    with pytest.raises(ValidationError):
        validate_username("   ")


# ---------------------------- hashing ---------------------------------------

def test_hash_is_argon2id_and_verifies():
    from security import hash_password, verify_password
    h = hash_password(VALID_PASSWORD)
    assert h.startswith("$argon2id$")
    assert verify_password(h, VALID_PASSWORD)
    assert not verify_password(h, BAD_PASSWORD)


def test_hashes_are_salted_per_call():
    from security import hash_password
    assert hash_password(VALID_PASSWORD) != hash_password(VALID_PASSWORD)


def test_verify_with_missing_hash_fails():
    from security import verify_password
    assert not verify_password(None, VALID_PASSWORD)
    assert not verify_password("", VALID_PASSWORD)


# ---------------------------- login behavior ----------------------------------

def test_login_wrong_password_rejected_generically(client, db):
    create_user(db, "Alice")
    response = client.post("/login",
                           data={"username": "Alice", "password": BAD_PASSWORD})
    assert response.status_code == 401
    assert b"Invalid username or password" in response.data
    # Must not reveal which part was wrong.
    assert b"user not found" not in response.data.lower()


def test_login_unknown_user_same_generic_message(client):
    response = client.post("/login",
                           data={"username": "ghost@example.com",
                                 "password": BAD_PASSWORD})
    assert response.status_code == 401
    assert b"Invalid username or password" in response.data


def test_legacy_user_without_password_cannot_login(client, db):
    """Users predating the refactor have NULL password_hash; they must be
    denied until an admin provisions a password."""
    db.execute("INSERT INTO users (username) VALUES ('OldTimer')")
    db.commit()
    response = client.post("/login",
                           data={"username": "OldTimer",
                                 "password": VALID_PASSWORD})
    assert response.status_code == 401
    assert b"Invalid username or password" in response.data


def test_login_empty_fields_rejected(client):
    response = client.post("/login", data={"username": "", "password": ""})
    assert response.status_code == 401
    assert b"Invalid username or password" in response.data


def test_successful_login_redirects_to_index(client, db):
    create_user(db, "Alice")
    response = client.post("/login",
                           data={"username": "Alice",
                                 "password": VALID_PASSWORD})
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_login_is_case_insensitive_for_username(client, db):
    create_user(db, "alice")
    response = login(client, username="ALICE")
    assert response.status_code == 200
    assert b"Log out (alice)" in response.data


def test_logout_clears_session(alice, client):
    client.get("/logout")
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ---------------------------- lockouts ---------------------------------------

def _fail_login(client, username="Alice"):
    client.post("/login", data={"username": username, "password": BAD_PASSWORD})


def test_lockout_after_five_failures(client, db):
    uid = create_user(db, "Alice")
    for _ in range(5):
        _fail_login(client)

    # Even CORRECT credentials are now rejected...
    response = login(client)
    assert response.status_code == 401
    # ...and a lockout row exists for the user key.
    row = db.execute("SELECT lock_key FROM lockouts WHERE lock_key = ?",
                     (f"user:{uid}",)).fetchone()
    assert row is not None


def test_ip_lock_blocks_other_users_too(client, db):
    """Five failures from one client lock the IP, so a DIFFERENT, perfectly
    valid account logging in from the same address is also blocked."""
    create_user(db, "Alice")
    create_user(db, "Bob")
    for _ in range(5):
        _fail_login(client)

    response = login(client, username="Bob")
    assert response.status_code == 401
    row = db.execute("SELECT lock_key FROM lockouts WHERE lock_key = ?",
                     ("ip:127.0.0.1",)).fetchone()
    assert row is not None


def test_four_failures_do_not_lock(client, db):
    create_user(db, "Alice")
    for _ in range(4):
        _fail_login(client)
    response = login(client)
    assert response.status_code == 200


def test_success_resets_user_counter_but_not_ip_counter(client, db):
    """The user's own failure counter clears on success, so alternating
    failures and successes never locks the account itself. The IP counter
    is cumulative by design: five total failures from one address locks
    that IP until an admin resets lockouts (manage_users.py
    reset-lockouts). Deliberately strict — there is no self-serve unlock."""
    create_user(db, "Alice")
    for _ in range(4):
        _fail_login(client)
    assert login(client).status_code == 200          # user counter cleared

    for _ in range(4):
        _fail_login(client)                           # IP now at 8 total
    assert login(client).status_code == 401           # IP lock engaged


def test_lockout_survives_new_client_instance(app, client, db):
    """Lockouts persist in the database, not memory — a brand-new client
    (fresh process/connection equivalent) is still blocked."""
    create_user(db, "Alice")
    for _ in range(5):
        _fail_login(client)

    fresh_client = app.test_client()
    response = login(fresh_client)
    assert response.status_code == 401


def test_reset_lockouts_restores_access(app, client, db):
    import security
    create_user(db, "Alice")
    for _ in range(5):
        _fail_login(client)
    assert login(client).status_code == 401

    with app.app_context():
        security.clear_all_lockouts(get_db_within(app))
    assert login(client).status_code == 200


def get_db_within(app):
    from db import get_db
    return get_db()


# ---------------------------- CSRF enforcement -------------------------------

def test_csrf_enforced_when_enabled(tmp_path, monkeypatch):
    """With CSRF protection on (as in production), a POST without a token
    is rejected with 400 before the view even runs."""
    monkeypatch.setattr(Config, "DB_PATH", str(tmp_path / "csrf_test.db"))
    from app import create_app

    class CsrfTestConfig(Config):
        TESTING = True
        SECRET_KEY = "csrf-test-secret"
        SESSION_COOKIE_SECURE = False
        # NOTE: WTF_CSRF_ENABLED deliberately left at its default (True).

    csrf_app = create_app(CsrfTestConfig)
    csrf_client = csrf_app.test_client()
    response = csrf_client.post("/login",
                                data={"username": "x", "password": "y" * 30})
    assert response.status_code == 400
    assert b"CSRF" in response.data or b"The CSRF token is missing" in response.data


# ---------------------------- production config -------------------------------

def test_production_session_flags():
    """Drift guard: the shipped Config must keep the hardened cookie flags.
    (The test config relaxes SECURE for plain-HTTP clients; production
    must not.)"""
    assert Config.SESSION_COOKIE_SECURE is True
    assert Config.SESSION_COOKIE_HTTPONLY is True
    assert Config.SESSION_COOKIE_SAMESITE == "Lax"


def test_passwords_never_stored_in_plaintext(client, db):
    from security import hash_password
    create_user(db, "Alice")
    row = db.execute("SELECT password_hash FROM users WHERE username='Alice'"
                     ).fetchone()
    assert row["password_hash"].startswith("$argon2")
    assert VALID_PASSWORD not in row["password_hash"]


# ------------------- regression: app works end to end -------------------------

def test_authenticated_flow_still_works(alice, client, db):
    """The refactor must not break the core workflow: create a return,
    change its status, see it in the history."""
    add_return(client, name="Smoke Test Corp")
    rid = return_id(db, "Smoke Test Corp")
    client.post(f"/returns/{rid}",
                data={"action": "change_status",
                      "new_status_id": str(status_id(db, "docs_waiting")),
                      "note": "smoke"},
                follow_redirects=True)
    row = db.execute("SELECT current_status_id FROM tax_returns WHERE id=?",
                     (rid,)).fetchone()
    assert row["current_status_id"] == status_id(db, "docs_waiting")