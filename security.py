"""Password policy, argon2 hashing, and login-lockout logic."""
import re
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from constants import (MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH,
                       PASSWORD_SPECIAL_CHARS, USERNAME_MAX_LEN)

_hasher = PasswordHasher()  # sensible defaults (argon2id)

# Precomputed hash of a random throwaway password. Verifying against it for
# unknown usernames keeps login timing uniform, hiding which users exist.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(32))

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,64}$")


class ValidationError(Exception):
    """Raised when a username or password fails policy checks."""


def validate_username(username):
    """Accept an email address OR a 3-64 char alphanumeric/underscore name."""
    username = (username or "").strip()
    if not username:
        raise ValidationError("Username is required.")
    if len(username) > USERNAME_MAX_LEN:
        raise ValidationError("Username exceeds 254 characters.")
    if "@" in username:
        if not _EMAIL_RE.match(username):
            raise ValidationError("Not a valid email address.")
    elif not _USERNAME_RE.match(username):
        raise ValidationError("Username must be 3-64 letters, digits, or "
                              "underscores (or a valid email address).")
    return username


def validate_password(password):
    """Enforce: 20-100 chars, >=1 lower, >=1 upper, >=1 digit, >=1 ASCII special."""
    if not isinstance(password, str) or not password:
        raise ValidationError("Password is required.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least "
                              f"{MIN_PASSWORD_LENGTH} characters long.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at most "
                              f"{MAX_PASSWORD_LENGTH} characters long.")
    if not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain a lowercase letter.")
    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain an uppercase letter.")
    if not re.search(r"[0-9]", password):
        raise ValidationError("Password must contain a digit.")
    if not any(c in PASSWORD_SPECIAL_CHARS for c in password):
        raise ValidationError("Password must contain a special character "
                              "(standard ASCII punctuation).")
    return password


def hash_password(password):
    """Return an argon2id hash of the password."""
    return _hasher.hash(password)


def verify_password(stored_hash, password):
    """Constant-ish verification; raises nothing, returns bool."""
    if not stored_hash:
        # Unknown user: burn the same CPU time as a real check.
        try:
            _hasher.verify(_DUMMY_HASH, password)
        except Exception:
            pass
        return False
    try:
        return _hasher.verify(stored_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# --------------------------- lockout tracking -------------------------------
# Persistent (SQLite) so a service restart does NOT unlock an attacker.
# Keys: "user:<id>" and "ip:<client ip>". Both user and IP are locked after
# either accumulates MAX_LOGIN_ATTEMPTS consecutive failures.

def _user_key(user_id):
    return f"user:{user_id}"


def _ip_key(ip):
    return f"ip:{ip or 'unknown'}"


def is_locked(db, user_id, ip):
    """True if the user key or IP key is currently locked."""
    row = db.execute(
        "SELECT 1 FROM lockouts WHERE lock_key IN (?, ?)",
        (_user_key(user_id) if user_id is not None else "\x00",
         _ip_key(ip))).fetchone()
    return row is not None


def record_failed_attempt(db, user_id, ip, max_attempts):
    """Increment failure counters for the user and IP; apply locks."""
    from constants import MAX_LOGIN_ATTEMPTS  # kept explicit for clarity
    for key in [_user_key(user_id) if user_id is not None else None, _ip_key(ip)]:
        if key is None:
            continue
        db.execute("""INSERT INTO failed_attempts (lock_key, count, last_attempt_at)
                      VALUES (?, 1, CURRENT_TIMESTAMP)
                      ON CONFLICT(lock_key) DO UPDATE
                      SET count = count + 1, last_attempt_at = CURRENT_TIMESTAMP""",
                   (key,))
        row = db.execute("SELECT count FROM failed_attempts WHERE lock_key=?",
                         (key,)).fetchone()
        if row and row["count"] >= MAX_LOGIN_ATTEMPTS:
            db.execute("INSERT OR IGNORE INTO lockouts (lock_key) VALUES (?)", (key,))
            db.execute("DELETE FROM failed_attempts WHERE lock_key=?", (key,))


def record_successful_login(db, user_id):
    """Clear the user's own failure counter (IP counter persists)."""
    db.execute("DELETE FROM failed_attempts WHERE lock_key=?",
               (_user_key(user_id),))


def clear_all_lockouts(db):
    """Admin action: unlock every user and IP, reset all counters."""
    db.execute("DELETE FROM lockouts")
    db.execute("DELETE FROM failed_attempts")
    db.commit()