"""Core blueprint: listing, creating, updating, archiving, exporting returns."""
import csv
import io
import datetime
import sqlite3
from flask import (Blueprint, request, redirect, url_for,
                   flash, render_template, send_file)

from helpers import current_user_id, parse_date
from db import get_db

returns_bp = Blueprint("returns", __name__)


# ---------------------------- main list ------------------------------------

@returns_bp.route("/")
def index():
    """Dashboard/list view with optional filtering by status, type,
    name search, and active/archived scope."""
    if current_user_id() is None:
        return redirect(url_for("auth.login"))
    db = get_db()
    status_filter = request.args.get("status", "")
    type_filter = request.args.get("type", "").strip()
    search = request.args.get("q", "").strip()
    show_archived = request.args.get("archived") == "1"

    # Base query includes each return's effective due date (extended date
    # overriding the original) and the most recent history entry that has
    # a note attached, to show "last note" on the list.
    sql = """
        SELECT r.id, r.return_name, r.tax_year, r.return_type,
               r.due_date, r.extended_due_date, r.archived_at,
               s.label AS status, s.stage_order,
               COALESCE(NULLIF(r.extended_due_date,''), r.due_date) AS effective_due,
               lastsh.note AS last_note, lastsh.changed_at AS last_note_at
        FROM tax_returns r
        JOIN statuses s ON s.id = r.current_status_id
        LEFT JOIN status_history lastsh ON lastsh.id =
            (SELECT sh.id FROM status_history sh
             WHERE sh.return_id = r.id AND sh.note IS NOT NULL
             ORDER BY sh.id DESC LIMIT 1)
        WHERE 1=1
    """
    params = []

    # Scope: archived or active returns.
    if show_archived:
        sql += " AND r.archived_at IS NOT NULL"
    else:
        sql += " AND r.archived_at IS NULL"

    if status_filter:
        sql += " AND r.current_status_id = ?"
        params.append(status_filter)
    if type_filter:
        sql += " AND r.return_type = ?"
        params.append(type_filter)
    if search:
        sql += " AND r.return_name LIKE ? COLLATE NOCASE"
        params.append(f"%{search}%")
    sql += " ORDER BY s.stage_order, r.return_name COLLATE NOCASE"
    returns = db.execute(sql, params).fetchall()

    today = datetime.date.today().isoformat()

    # Dashboard counts per status. LEFT JOIN with a r.id guard so empty
    # statuses don't get a phantom count of 1.
    dash_sql = """
        SELECT s.label, s.stage_order,
               COUNT(CASE WHEN r.id IS NOT NULL AND r.archived_at IS NULL
                          THEN 1 END) AS active_count,
               COUNT(CASE WHEN r.archived_at IS NOT NULL THEN 1 END) AS archived_count
        FROM statuses s
        LEFT JOIN tax_returns r ON r.current_status_id = s.id
        GROUP BY s.id, s.label, s.stage_order
        ORDER BY s.stage_order
    """
    counts = db.execute(dash_sql).fetchall()

    return render_template("index.html", returns=returns, today=today,
                           status_filter=status_filter, type_filter=type_filter,
                           search=search, show_archived=show_archived,
                           counts=counts)


# ---------------------------- add return -----------------------------------

@returns_bp.route("/returns/new", methods=["GET", "POST"])
def new_return():
    """Form to create a new tax return (starts at 'Not Started')."""
    if current_user_id() is None:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        db = get_db()
        name = request.form.get("return_name", "").strip()
        year = request.form.get("tax_year", "").strip()
        rtype = request.form.get("return_type", "").strip()
        due = parse_date(request.form.get("due_date", ""))
        ext = parse_date(request.form.get("extended_due_date", ""))

        if not (name and year and rtype):
            flash("Return name, tax year, and return type are required.")
        else:
            try:
                # Insert the return at 'not_started'...
                cur = db.execute("""INSERT INTO tax_returns
                    (return_name, tax_year, return_type, due_date,
                     extended_due_date, current_status_id, created_by)
                    VALUES (?,?,?,?,?,
                      (SELECT id FROM statuses WHERE code='not_started'), ?)""",
                    (name, int(year), rtype, due, ext, current_user_id()))
                # ...and record its creation as the first history entry.
                db.execute("""INSERT INTO status_history
                    (return_id, old_status_id, new_status_id, changed_by, note)
                    VALUES (?, NULL,
                      (SELECT id FROM statuses WHERE code='not_started'), ?, NULL)""",
                    (cur.lastrowid, current_user_id()))
                db.commit()
                flash(f"Added return: {name} ({year} {rtype}).")
                return redirect(url_for("returns.index"))
            except sqlite3.IntegrityError:
                flash("A return with that name, year, and type already exists.")
            except ValueError:
                flash("Tax year must be a number.")
    return render_template("new_return.html")


# ---------------------------- detail / status change ------------------------

@returns_bp.route("/returns/<int:return_id>", methods=["GET", "POST"])
def return_detail(return_id):
    """Single-return view: change status, edit due dates, see history."""
    if current_user_id() is None:
        return redirect(url_for("auth.login"))
    db = get_db()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "change_status":
            new_status_id = request.form.get("new_status_id")
            note = request.form.get("note", "").strip()
            # Validate both the target status and the return itself.
            status_exists = db.execute("SELECT id FROM statuses WHERE id=?",
                                       (new_status_id,)).fetchone()
            ret = db.execute("SELECT current_status_id FROM tax_returns WHERE id=?",
                             (return_id,)).fetchone()
            if not status_exists or not ret:
                flash("Invalid status or return.")
            else:
                with db:  # history insert + return update happen atomically
                    db.execute("""INSERT INTO status_history
                        (return_id, old_status_id, new_status_id, changed_by, note)
                        VALUES (?,?,?,?,?)""",
                        (return_id, ret["current_status_id"],
                         int(new_status_id), current_user_id(), note or None))
                    db.execute("UPDATE tax_returns SET current_status_id=? WHERE id=?",
                               (int(new_status_id), return_id))
                flash("Status updated.")
                return redirect(url_for("returns.return_detail", return_id=return_id))

        elif action == "update_dates":
            due = parse_date(request.form.get("due_date", ""))
            ext = parse_date(request.form.get("extended_due_date", ""))
            with db:
                db.execute("""UPDATE tax_returns SET due_date=?, extended_due_date=?
                              WHERE id=?""", (due, ext, return_id))
            flash("Due dates updated.")
            return redirect(url_for("returns.return_detail", return_id=return_id))

    row = db.execute("""
        SELECT r.*, s.label AS status, s.stage_order
        FROM tax_returns r
        JOIN statuses s ON s.id = r.current_status_id WHERE r.id=?
    """, (return_id,)).fetchone()
    if row is None:
        flash("Return not found.")
        return redirect(url_for("returns.index"))

    # Full audit trail, newest first.
    history = db.execute("""
        SELECT sh.changed_at, sh.note, os.label AS old_status, ns.label AS new_status,
               u.username
        FROM status_history sh
        JOIN statuses ns ON ns.id = sh.new_status_id
        LEFT JOIN statuses os ON os.id = sh.old_status_id
        LEFT JOIN users u ON u.id = sh.changed_by
        WHERE sh.return_id = ?
        ORDER BY sh.changed_at DESC, sh.id DESC
    """, (return_id,)).fetchall()
    return render_template("detail.html", r=row, history=history)


# ---------------------------- archive / unarchive ---------------------------

@returns_bp.route("/returns/<int:return_id>/archive", methods=["POST"])
def archive_return(return_id):
    """Soft-archive or restore a return; status history is always preserved."""
    if current_user_id() is None:
        return redirect(url_for("auth.login"))
    db = get_db()
    action = request.form.get("archive_action", "archive")
    row = db.execute("SELECT return_name FROM tax_returns WHERE id=?",
                     (return_id,)).fetchone()
    if row is None:
        flash("Return not found.")
        return redirect(url_for("returns.index"))

    if action == "unarchive":
        with db:
            db.execute("UPDATE tax_returns SET archived_at=NULL WHERE id=?",
                       (return_id,))
        flash(f"Restored return: {row['return_name']}.")
        # Stay in whichever view the user was in.
        return redirect(url_for("returns.index", archived="1" if False else None))
    else:
        with db:
            db.execute("UPDATE tax_returns SET archived_at=CURRENT_TIMESTAMP WHERE id=?",
                       (return_id,))
        flash(f"Archived return: {row['return_name']}.")
        return redirect(url_for("returns.index", archived="1"))


# ---------------------------- CSV export ------------------------------------

@returns_bp.route("/returns/export-csv")
def export_csv():
    """Download the current view's returns (active or archived) as CSV."""
    if current_user_id() is None:
        return redirect(url_for("auth.login"))
    db = get_db()
    show_archived = request.args.get("archived") == "1"

    sql = """
        SELECT r.return_name, r.tax_year, r.return_type,
               r.due_date, r.extended_due_date, r.archived_at,
               s.label AS status, r.created_at
        FROM tax_returns r
        JOIN statuses s ON s.id = r.current_status_id
        WHERE 1=1
    """
    params = []
    if show_archived:
        sql += " AND r.archived_at IS NOT NULL"
    else:
        sql += " AND r.archived_at IS NULL"
    sql += " ORDER BY s.stage_order, r.return_name"
    rows = db.execute(sql, params).fetchall()

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["Return Name", "Tax Year", "Type", "Status", "Due Date",
                     "Extended Due Date", "Archived At", "Created At"])
    for row in rows:
        writer.writerow([
            row["return_name"], row["tax_year"], row["return_type"],
            row["status"], row["due_date"] or "", row["extended_due_date"] or "",
            row["archived_at"] or "", row["created_at"]
        ])

    filename = (f"tax_returns_{'archived' if show_archived else 'active'}_"
                f"{datetime.date.today().isoformat()}.csv")
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename
    )