"""Core blueprint: listing, creating, updating, archiving, exporting returns."""
import csv
import io
import re
import datetime
import sqlite3
from flask import (Blueprint, request, redirect, url_for, flash, render_template, send_file)
from constants import KANBAN_COLUMNS
from helpers import current_user_id, parse_date
from db import get_db

returns_bp = Blueprint("returns", __name__)

# Human-readable labels for audit-log change types.
CHANGE_TYPE_LABELS = {
    "status": "Status",
    "signer": "Signer",
    "dates": "Due Dates",
}


def _record_history(db, return_id, changed_by, change_type, note,
                    old_status_id=None, new_status_id=None):
    """Insert one audit-trail row into status_history.

    For field edits (signer, dates), old_status_id and new_status_id
    should both be the return's current status — the workflow status
    did not change, but recording it keeps referential integrity and
    lets the history table show where the return sat at the time.
    """
    db.execute("""INSERT INTO status_history
        (return_id, old_status_id, new_status_id, changed_by, note, change_type)
        VALUES (?,?,?,?,?,?)""",
        (return_id, old_status_id, new_status_id, changed_by, note, change_type))


# ---------------------------- main list ------------------------------------

@returns_bp.route("/")
def index():
    """Dashboard/list view with optional filtering by status, type,
    signer search, name search, and active/archived scope."""
    if current_user_id() is None:
        return redirect(url_for("auth.login"))
    db = get_db()
    status_filter = request.args.get("status", "")
    type_filter = request.args.get("type", "").strip()
    signer_filter = request.args.get("signer", "").strip()
    search = request.args.get("q", "").strip()
    show_archived = request.args.get("archived") == "1"

    sql = """
        SELECT r.id, r.return_name, r.tax_year, r.return_type,
               r.due_date, r.extended_due_date, r.archived_at, r.signer,
               s.label AS status, s.stage_order,
               COALESCE(NULLIF(r.extended_due_date,''), r.due_date) AS effective_due,
               lastsh.note AS last_note, lastsh.changed_at AS last_note_at
        FROM tax_returns r
        JOIN statuses s ON s.id = r.current_status_id
        LEFT JOIN status_history lastsh ON lastsh.id =
            (SELECT sh.id FROM status_history sh
             WHERE sh.return_id = r.id AND sh.note IS NOT NULL AND sh.change_type = 'status'
             ORDER BY sh.id DESC LIMIT 1)
        WHERE 1=1
    """
    params = []
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
    if signer_filter:
        sql += " AND r.signer LIKE ? COLLATE NOCASE"
        params.append(f"%{signer_filter}%")
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

    # Distinct signers currently used, for the filter dropdown.
    distinct_signers = [row["signer"] for row in db.execute("""
        SELECT DISTINCT signer FROM tax_returns
        WHERE signer IS NOT NULL AND TRIM(signer) != ''
        ORDER BY signer COLLATE NOCASE
    """).fetchall()]

    return render_template("index.html", returns=returns, today=today,
                           status_filter=status_filter, type_filter=type_filter,
                           signer_filter=signer_filter,
                           search=search, show_archived=show_archived,
                           counts=counts, distinct_signers=distinct_signers)

# ---------------------------- board (kanban) ------------------------------------

@returns_bp.route("/board")
def board():
    """Kanban board: active returns grouped into four workflow columns
    (Not Started, Preparing, In Review, Completed) with per-column
    counts, filterable by return type, signer, and name search."""
    if current_user_id() is None:
        return redirect(url_for("auth.login"))
    db = get_db()
    type_filter = request.args.get("type", "").strip()
    signer_filter = request.args.get("signer", "").strip()
    search = request.args.get("q", "").strip()
    show_archived = request.args.get("archived") == "1"

    sql = """
        SELECT r.id, r.return_name, r.tax_year, r.return_type,
               r.due_date, r.extended_due_date, r.archived_at, r.signer,
               s.label AS status, s.stage_order, s.code AS status_code,
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
    if show_archived:
        sql += " AND r.archived_at IS NOT NULL"
    else:
        sql += " AND r.archived_at IS NULL"
    if type_filter:
        sql += " AND r.return_type = ?"
        params.append(type_filter)
    if signer_filter:
        sql += " AND r.signer LIKE ? COLLATE NOCASE"
        params.append(f"%{signer_filter}%")
    if search:
        sql += " AND r.return_name LIKE ? COLLATE NOCASE"
        params.append(f"%{search}%")
    sql += " ORDER BY s.stage_order, r.return_name COLLATE NOCASE"
    returns = db.execute(sql, params).fetchall()

    # Bucket returns into the four kanban columns. Counts derive from
    # the (possibly filtered) result set so the header badges stay
    # accurate while a filter or search is active.
    columns = []
    for col_title, status_codes in KANBAN_COLUMNS:
        col_returns = [r for r in returns if r["status_code"] in status_codes]
        columns.append({
            "title": col_title,
            "count": len(col_returns),
            "returns": col_returns,
        })

    today = datetime.date.today().isoformat()

    # Distinct signers currently used, for the filter dropdown.
    distinct_signers = [row["signer"] for row in db.execute("""
        SELECT DISTINCT signer FROM tax_returns
        WHERE signer IS NOT NULL AND TRIM(signer) != ''
        ORDER BY signer COLLATE NOCASE
    """).fetchall()]

    return render_template("board.html", returns=returns, today=today,
                           type_filter=type_filter, signer_filter=signer_filter,
                           search=search, show_archived=show_archived,
                           columns=columns, distinct_signers=distinct_signers)

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
        signer = request.form.get("signer", "").strip()

        if not (name and year and rtype):
            flash("Return name, tax year, and return type are required.")
        else:
            try:
                # Insert the return at 'not_started'...
                cur = db.execute("""INSERT INTO tax_returns
                    (return_name, tax_year, return_type, due_date,
                     extended_due_date, signer, current_status_id, created_by)
                    VALUES (?,?,?,?,?,?,
                      (SELECT id FROM statuses WHERE code='not_started'), ?)""",
                    (name, int(year), rtype, due, ext, signer or None,
                     current_user_id()))
                # ...and record its creation as the first history entry.
                _record_history(
                    db, cur.lastrowid, current_user_id(), "status",
                    f"Return created (signer: {signer or 'none'}; "
                    f"due: {due or 'none'}; extended due: {ext or 'none'})",
                    old_status_id=None,
                    new_status_id=db.execute(
                        "SELECT id FROM statuses WHERE code='not_started'"
                    ).fetchone()["id"])
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
    """Single-return view: change status, edit due dates, edit signer,
    see history."""
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
                    _record_history(
                        db, return_id, current_user_id(), "status",
                        note or None,
                        old_status_id=ret["current_status_id"],
                        new_status_id=int(new_status_id))
                    db.execute("UPDATE tax_returns SET current_status_id=? WHERE id=?",
                               (int(new_status_id), return_id))
                flash("Status updated.")
                return redirect(url_for("returns.return_detail", return_id=return_id))

        elif action == "update_dates":
            due = parse_date(request.form.get("due_date", ""))
            ext = parse_date(request.form.get("extended_due_date", ""))
            ret = db.execute(
                "SELECT due_date, extended_due_date, current_status_id "
                "FROM tax_returns WHERE id=?", (return_id,)).fetchone()
            if ret is None:
                flash("Return not found.")
                return redirect(url_for("returns.index"))
            # Audit-log the change (only if something actually changed).
            changes = []
            if (ret["due_date"] or "") != (due or ""):
                changes.append(
                    f"due date {ret['due_date'] or 'none'} → {due or 'none'}")
            if (ret["extended_due_date"] or "") != (ext or ""):
                changes.append(
                    f"extended due date {ret['extended_due_date'] or 'none'} → "
                    f"{ext or 'none'}")
            with db:
                if changes:
                    _record_history(
                        db, return_id, current_user_id(), "dates",
                        "Changed " + "; ".join(changes),
                        old_status_id=ret["current_status_id"],
                        new_status_id=ret["current_status_id"])
                db.execute("""UPDATE tax_returns SET due_date=?, extended_due_date=?
                              WHERE id=?""", (due, ext, return_id))
            flash("Due dates updated.")
            return redirect(url_for("returns.return_detail", return_id=return_id))

        elif action == "update_signer":
            signer = request.form.get("signer", "").strip()
            ret = db.execute(
                "SELECT signer, current_status_id FROM tax_returns WHERE id=?",
                (return_id,)).fetchone()
            if ret is None:
                flash("Return not found.")
                return redirect(url_for("returns.index"))
            with db:
                if (ret["signer"] or "") != signer:
                    _record_history(
                        db, return_id, current_user_id(), "signer",
                        f"Signer changed: {ret['signer'] or 'none'} → {signer or 'none'}",
                        old_status_id=ret["current_status_id"],
                        new_status_id=ret["current_status_id"])
                db.execute("UPDATE tax_returns SET signer=? WHERE id=?",
                           (signer or None, return_id))
            flash("Signer updated.")
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
               u.username, sh.change_type
        FROM status_history sh
        JOIN statuses ns ON ns.id = sh.new_status_id
        LEFT JOIN statuses os ON os.id = sh.old_status_id
        LEFT JOIN users u ON u.id = sh.changed_by
        WHERE sh.return_id = ?
        ORDER BY sh.changed_at DESC, sh.id DESC
    """, (return_id,)).fetchall()
    return render_template("detail.html", r=row, history=history,
                           change_labels=CHANGE_TYPE_LABELS)

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
        # No flash on restore; go straight to the detail page
        return redirect(url_for("returns.return_detail", return_id=return_id))
    else:
        with db:
            db.execute("UPDATE tax_returns SET archived_at=CURRENT_TIMESTAMP WHERE id=?",
                       (return_id,))
        # No flash on archive; go back to the active list
        return redirect(url_for("returns.index"))

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
               r.due_date, r.extended_due_date, r.archived_at, r.signer,
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
                     "Extended Due Date", "Signer", "Archived At", "Created At"])
    for row in rows:
        writer.writerow([
            row["return_name"], row["tax_year"], row["return_type"],
            row["status"], row["due_date"] or "", row["extended_due_date"] or "",
            row["signer"] or "", row["archived_at"] or "", row["created_at"]
        ])

    filename = (f"tax_returns_{'archived' if show_archived else 'active'}_"
                f"{datetime.date.today().isoformat()}.csv")
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename
    )

# ---------------------------- CSV import -------------------------------------

# Header aliases: maps a normalized CSV header (lowercase, punctuation
# stripped) to the canonical field name we insert with.
IMPORT_ALIASES = {
    "returnname": "return_name",  "name": "return_name",
    "taxyear": "tax_year",        "year": "tax_year",
    "returntype": "return_type",  "type": "return_type",
    "duedate": "due_date",        "due": "due_date",
    "extendedduedate": "extended_due_date", "extendeddue": "extended_due_date",
    "signer": "signer",
    "status": "status",
}


def _norm(s):
    """Normalize a header or status value: lowercase, strip punctuation/spaces."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


@returns_bp.route("/returns/import-csv", methods=["POST"])
def import_csv():
    """Bulk-add returns from an uploaded CSV file.

    Required columns: return name, tax year, return type (headers are
    matched case/punctuation-insensitively). Optional: due date,
    extended due date, signer, status.
    """
    if current_user_id() is None:
        return redirect(url_for("auth.login"))
    file = request.files.get("csv_file")
    if file is None or file.filename == "":
        flash("Please choose a CSV file to import.")
        return redirect(url_for("returns.index"))

    # utf-8-sig strips the BOM if Excel exported the file.
    try:
        text = file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        flash("Could not read the file as UTF-8 text.")
        return redirect(url_for("returns.index"))

    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        flash("The uploaded CSV file is empty.")
        return redirect(url_for("returns.index"))

    # Map each CSV column to a canonical field via the alias table.
    header_map = {}
    for idx, header in enumerate(rows[0]):
        canon = IMPORT_ALIASES.get(_norm(header))
        if canon and canon not in header_map.values():
            header_map[idx] = canon

    missing = [req for req in ("return_name", "tax_year", "return_type")
               if req not in header_map.values()]
    if missing:
        flash(f"CSV is missing required column(s): {', '.join(missing)}. "
              "Expected headers like 'Return Name', 'Tax Year', 'Return Type'.")
        return redirect(url_for("returns.index"))

    db = get_db()
    statuses_by_key = {}
    for s in db.execute("SELECT id, code, label FROM statuses").fetchall():
        statuses_by_key[_norm(s["code"])] = s["id"]
        statuses_by_key[_norm(s["label"])] = s["id"]
    default_status_id = db.execute(
        "SELECT id FROM statuses WHERE code='not_started'").fetchone()["id"]

    added, duplicates, errors = [], [], []
    for rownum, raw in enumerate(rows[1:], start=2):  # row 1 = header
        rec = {}
        for idx, field in header_map.items():
            rec[field] = raw[idx].strip() if idx < len(raw) else ""

        name, year, rtype = (rec.get("return_name", ""),
                              rec.get("tax_year", ""),
                              rec.get("return_type", ""))
        if not (name and year and rtype):
            errors.append(f"row {rownum}: return name, tax year, and "
                          "return type are required")
            continue

        try:
            year_val = int(year)
        except ValueError:
            errors.append(f"row {rownum}: tax year '{year}' is not a number")
            continue

        due = parse_date(rec.get("due_date", ""))
        if rec.get("due_date") and due is None:
            errors.append(f"row {rownum}: invalid due date "
                          f"'{rec['due_date']}' (use YYYY-MM-DD or MM/DD/YYYY)")
            continue
        ext = parse_date(rec.get("extended_due_date", ""))
        if rec.get("extended_due_date") and ext is None:
            errors.append(f"row {rownum}: invalid extended due date "
                          f"'{rec['extended_due_date']}'")
            continue

        status_id = default_status_id
        if rec.get("status"):
            status_id = statuses_by_key.get(_norm(rec["status"]))
            if status_id is None:
                errors.append(f"row {rownum}: unknown status "
                              f"'{rec['status']}' (row skipped)")
                continue

        signer = rec.get("signer", "")
        try:
            cur = db.execute("""INSERT INTO tax_returns
                (return_name, tax_year, return_type, due_date,
                 extended_due_date, signer, current_status_id, created_by)
                VALUES (?,?,?,?,?,?,?,?)""",
                (name, year_val, rtype, due, ext, signer or None,
                 status_id, current_user_id()))
            _record_history(
                db, cur.lastrowid, current_user_id(), "status",
                f"Imported from CSV (signer: {signer or 'none'}; "
                f"due: {due or 'none'}; extended due: {ext or 'none'})",
                old_status_id=None, new_status_id=status_id)
            db.commit()
            added.append(name)
        except sqlite3.IntegrityError:
            db.rollback()
            duplicates.append(f"{name} ({year} {rtype})")
        except sqlite3.DatabaseError:
            db.rollback()
            errors.append(f"row {rownum}: database error while inserting")

    # Report results.
    summary = [f"Import complete: {len(added)} return(s) added."]
    if duplicates:
        summary.append(f"{len(duplicates)} duplicate(s) skipped: "
                       + ", ".join(duplicates[:10])
                       + ("…" if len(duplicates) > 10 else ""))
    flash(" ".join(summary))
    for e in errors[:10]:  # keep flash spam bounded
        flash(f"CSV import — {e}")
    if len(errors) > 10:
        flash(f"…and {len(errors) - 10} more error(s).")

    return redirect(url_for("returns.index"))