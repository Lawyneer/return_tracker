#!/usr/bin/env python3
"""Admin CLI for managing users of the Tax Return Status Tracker.

Usage (run from the project directory):
  python manage_users.py add <username>            # create user, prompt for password
  python manage_users.py set-password <username>   # set/change password (also for legacy users)
  python manage_users.py list                      # list users and password status
  python manage_users.py reset-lockouts            # clear all login lockouts & failure counts
  python manage_users.py lock-status                # show current lockouts and failed attempts

Usernames: an email address, or 3-64 alphanumeric/underscore characters.
Passwords: 20-100 chars with lowercase, uppercase, digit, and ASCII special.

Examples:
  python manage_users.py add jane@example.com
  python manage_users.py set-password bob
  python manage_users.py reset-lockouts
"""
import argparse
import getpass
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config                       # noqa: E402
import security                                  # noqa: E402
from db import init_db                           # noqa: E402


def _connect():
    init_db()  # ensures migrations ran even if the web app hasn't started
    db = sqlite3.connect(Config.DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def _prompt_password():
    """Prompt twice on the terminal (input hidden); enforce policy."""
    while True:
        pw1 = getpass.getpass("Password (input hidden): ")
        pw2 = getpass.getpass("Confirm password: ")
        if pw1 != pw2:
            print("  Passwords do not match. Try again.")
            continue
        try:
            security.validate_password(pw1)
            return pw1
        except security.ValidationError as e:
            print(f"  POLICY ERROR: {e}")
            print("  Choose a stronger password and try again.")


def cmd_add(args):
    db = _connect()
    try:
        username = security.validate_username(args.username)
    except security.ValidationError as e:
        sys.exit(f"Invalid username: {e}")
    if db.execute("SELECT 1 FROM users WHERE username=? COLLATE NOCASE",
                  (username,)).fetchone():
        sys.exit(f"User '{username}' already exists (usernames are case-insensitive). "
                 "Use 'set-password' instead.")
    password = _prompt_password()
    with db:
        db.execute("INSERT INTO users (username, password_hash) VALUES (?,?)",
                   (username, security.hash_password(password)))
    print(f"User '{username}' created with password set.")


def cmd_set_password(args):
    db = _connect()
    row = db.execute("SELECT id, username FROM users WHERE username=? COLLATE NOCASE",
                     (args.username,)).fetchone()
    if not row:
        sys.exit(f"No user named '{args.username}'. Use 'list' to see users.")
    password = _prompt_password()
    with db:
        db.execute("UPDATE users SET password_hash=? WHERE id=?",
                   (security.hash_password(password), row["id"]))
    print(f"Password set for '{row['username']}'.")


def cmd_list(_args):
    db = _connect()
    rows = db.execute("SELECT id, username, created_at, "
                      "CASE WHEN password_hash IS NULL THEN 'NO PASSWORD (cannot log in)' "
                      "ELSE 'ok' END AS pw "
                      "FROM users ORDER BY username COLLATE NOCASE").fetchall()
    if not rows:
        print("No users.")
        return
    for r in rows:
        print(f"  {r['id']:>4}  {r['username']:<40}  {r['pw']:<32}  {r['created_at']}")


def cmd_reset_lockouts(_args):
    db = _connect()
    with db:
        security.clear_all_lockouts(db)
    print("All lockouts cleared and failure counters reset.")


def cmd_lock_status(_args):
    db = _connect()
    lockouts = db.execute("SELECT * FROM lockouts ORDER BY locked_at").fetchall()
    attempts = db.execute("SELECT * FROM failed_attempts "
                          "ORDER BY last_attempt_at DESC").fetchall()
    print("Active lockouts:")
    for r in lockouts:
        print(f"  {r['lock_key']:<50}  locked at {r['locked_at']}")
    if not lockouts:
        print("  (none)")
    print("\nRecent failed-attempt counters:")
    for r in attempts:
        print(f"  {r['lock_key']:<50}  {r['count']} attempt(s), last {r['last_attempt_at']}")
    if not attempts:
        print("  (none)")


def main():
    parser = argparse.ArgumentParser(
        description="Manage users and lockouts for the Tax Return Tracker.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="Create a new user (prompts for password)")
    p.add_argument("username")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("set-password",
                       help="Set/reset a user's password (also enables legacy users)")
    p.add_argument("username")
    p.set_defaults(func=cmd_set_password)

    sub.add_parser("list", help="List users").set_defaults(func=cmd_list)
    sub.add_parser("reset-lockouts",
                   help="Clear all login lockouts").set_defaults(func=cmd_reset_lockouts)
    sub.add_parser("lock-status",
                   help="Show lockouts and failed attempts").set_defaults(func=cmd_lock_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()