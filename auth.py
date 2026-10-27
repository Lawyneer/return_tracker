"""Authentication (username + password) and appearance routes."""
from flask import (Blueprint, g, request, session,
                   redirect, url_for, flash, render_template)

from helpers import current_user_id
from db import get_db
from constants import DEFAULT_THEME
import security

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Sign in with username/email and password.

    Security notes:
    - Generic error messages (never reveals whether username or password
      was wrong, or whether the user exists).
    - Brute-force lockout: after MAX_LOGIN_ATTEMPTS consecutive failures
      the username AND the client IP are locked until an admin resets
      them (manage_users.py reset-lockouts).
    - Session is regenerated on login to prevent session fixation.
    """
    db = get_db()
    if request.method == "POST":
        username = (request.form.get("username", "") or "").strip()
        password = request.form.get("password", "") or ""
        ip = request.remote_addr

        if not username or not password:
            flash("Invalid username or password.")
            return render_template("login.html"), 401

        row = db.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            (username,)).fetchone()

        # Lockout check first — do not reveal lock status for valid
        # usernames either; same generic message.
        locked = security.is_locked(
            db, row["id"] if row else None, ip)
        if locked:
            flash("Invalid username or password.")
            return render_template("login.html"), 401

        ok = security.verify_password(row["password_hash"] if row else None,
                                      password)

        if row and ok:
            # Success: clear this user's failure counter, regenerate session.
            security.record_successful_login(db, row["id"])
            db.commit()
            session.clear()   # prevents session fixation
            session["user_id"] = row["id"]
            session["username"] = row["username"]
            return redirect(url_for("returns.index"))

        # Failure: count it against the user (if known) and the IP.
        security.record_failed_attempt(
            db, row["id"] if row else None, ip,
            getattr(security, "MAX_LOGIN_ATTEMPTS", 5))
        db.commit()
        flash("Invalid username or password.")
        return render_template("login.html"), 401

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Clear the session and return to the login page."""
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/toggle-theme")
def toggle_theme():
    """Flip the user's dark/light preference and go back where they came from."""
    session["theme"] = "light" if session.get("theme", DEFAULT_THEME) != "light" else "dark"
    return redirect(request.referrer or url_for("returns.index"))