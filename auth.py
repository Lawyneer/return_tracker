"""Authentication and appearance routes (dropdown-based login)."""
import sqlite3
from flask import (Blueprint, g, request, session,
                   redirect, url_for, flash, render_template)

from helpers import current_user_id
from db import get_db
from constants import DEFAULT_THEME

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Sign in as an existing user or create a new user by name.

    Note: this is intentionally lightweight (no passwords) — it identifies
    who made changes, it is not real security. Protect the deployment
    accordingly if exposed beyond a trusted network.
    """
    db = get_db()  # lazily opens (or reuses) the request-scoped connection
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add_user":
            name = request.form.get("new_username", "").strip()
            if name:
                try:
                    db.execute("INSERT INTO users (username) VALUES (?)", (name,))
                    db.commit()
                    flash(f"User '{name}' added.")
                except sqlite3.IntegrityError:
                    flash("That username already exists.")
            return redirect(url_for("auth.login"))

        elif action == "login":
            uid = request.form.get("user_id")
            row = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
            if row:
                session["user_id"] = row["id"]
                session["username"] = row["username"]
                return redirect(url_for("returns.index"))
            flash("Please select a valid user.")

    users = db.execute("SELECT * FROM users ORDER BY username").fetchall()
    return render_template("login.html", users=users)

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