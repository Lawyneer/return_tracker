"""Signer field, extended audit trail (change_type), and CSV import."""
import io

from tests.conftest import add_return, return_id, status_id


# ---------------------------- signer field ----------------------------------

def test_signer_set_at_creation(alice, client, db):
    add_return(client, name="Signed Corp", signer="Jane Smith")
    rid = return_id(db, "Signed Corp")
    row = db.execute("SELECT signer FROM tax_returns WHERE id = ?",
                     (rid,)).fetchone()
    assert row["signer"] == "Jane Smith"

    assert b"Jane Smith" in client.get("/").data
    assert b"Jane Smith" in client.get(f"/returns/{rid}").data
    assert b"Jane Smith" in client.get("/board").data


def test_signer_blank_stored_as_null(alice, client, db):
    add_return(client, name="Unsigned Corp", signer="")
    rid = return_id(db, "Unsigned Corp")
    row = db.execute("SELECT signer FROM tax_returns WHERE id = ?",
                     (rid,)).fetchone()
    assert row["signer"] is None


def test_signer_edit_updates_return_and_logs_history(alice, client, db):
    add_return(client, name="Reassigned Corp")
    rid = return_id(db, "Reassigned Corp")

    client.post(f"/returns/{rid}",
                data={"action": "update_signer", "signer": "John Doe"},
                follow_redirects=True)

    row = db.execute("SELECT signer FROM tax_returns WHERE id = ?",
                     (rid,)).fetchone()
    assert row["signer"] == "John Doe"

    history = db.execute("""SELECT change_type, note, changed_by
                            FROM status_history
                            WHERE return_id = ? ORDER BY id DESC LIMIT 1""",
                         (rid,)).fetchone()
    assert history["change_type"] == "signer"
    assert "John Doe" in history["note"]
    assert history["changed_by"] == alice


def test_signer_noop_edit_not_logged(alice, client, db):
    """Saving the same signer again must not write an audit row."""
    add_return(client, name="Same Signer Corp", signer="John Doe")
    rid = return_id(db, "Same Signer Corp")
    before = db.execute("SELECT COUNT(*) AS n FROM status_history").fetchone()["n"]

    client.post(f"/returns/{rid}",
                data={"action": "update_signer", "signer": "John Doe"},
                follow_redirects=True)

    after = db.execute("SELECT COUNT(*) AS n FROM status_history").fetchone()["n"]
    assert before == after


def test_signer_filter_on_index(alice, client):
    add_return(client, name="Janes Corp", signer="Jane Smith")
    add_return(client, name="Bobs Corp", rtype="1040", signer="Bob Jones")

    page = client.get("/?signer=Jane%20Smith")
    assert b"Janes Corp" in page.data
    assert b"Bobs Corp" not in page.data

    # Dropdown offers exactly the signers in use.
    page = client.get("/")
    assert page.data.count(b'<option value="Jane Smith"') == 1


def test_signer_filter_on_board(alice, client):
    add_return(client, name="Janes Corp", signer="Jane Smith")
    add_return(client, name="Bobs Corp", rtype="1040", signer="Bob Jones")

    page = client.get("/board?signer=Jane%20Smith")
    assert b"Janes Corp" in page.data
    assert b"Bobs Corp" not in page.data


def test_csv_export_includes_signer(alice, client):
    add_return(client, name="Export Signed Corp", signer="Jane Smith")
    response = client.get("/returns/export-csv")
    assert b"Signer" in response.data
    assert b"Jane Smith" in response.data


# ----------------------- extended audit trail -------------------------------

def test_date_edit_logs_history(alice, client, db):
    add_return(client, name="Rescheduled Corp", due="2026-04-15")
    rid = return_id(db, "Rescheduled Corp")

    client.post(f"/returns/{rid}",
                data={"action": "update_dates",
                      "due_date": "2026-10-15",
                      "extended_due_date": "2027-01-15"},
                follow_redirects=True)

    row = db.execute("""SELECT due_date, extended_due_date FROM tax_returns
                        WHERE id = ?""", (rid,)).fetchone()
    assert row["due_date"] == "2026-10-15"
    assert row["extended_due_date"] == "2027-01-15"

    history = db.execute("""SELECT change_type, note
                            FROM status_history
                            WHERE return_id = ? ORDER BY id DESC LIMIT 1""",
                         (rid,)).fetchone()
    assert history["change_type"] == "dates"
    assert "2026-10-15" in history["note"]


def test_date_edit_noop_not_logged(alice, client, db):
    add_return(client, name="Steady Dates Corp", due="2026-04-15", ext="2026-10-15")
    rid = return_id(db, "Steady Dates Corp")
    before = db.execute("SELECT COUNT(*) AS n FROM status_history").fetchone()["n"]

    client.post(f"/returns/{rid}",
                data={"action": "update_dates",
                      "due_date": "2026-04-15",
                      "extended_due_date": "2026-10-15"},
                follow_redirects=True)

    after = db.execute("SELECT COUNT(*) AS n FROM status_history").fetchone()["n"]
    assert before == after


def test_status_history_change_type_is_status(alice, client, db):
    """Ordinary status changes remain labeled 'status' after the
    change_type column was introduced."""
    add_return(client)
    rid = return_id(db)
    client.post(f"/returns/{rid}",
                data={"action": "change_status",
                      "new_status_id": str(status_id(db, "docs_waiting"))},
                follow_redirects=True)

    history = db.execute("""SELECT change_type FROM status_history
                            WHERE return_id = ? ORDER BY id DESC LIMIT 1""",
                         (rid,)).fetchone()
    assert history["change_type"] == "status"


def test_detail_page_shows_change_column(alice, client, db):
    """The history table distinguishes Status / Signer / Due Dates."""
    add_return(client, name="Mixed Edits Corp")
    rid = return_id(db, "Mixed Edits Corp")
    client.post(f"/returns/{rid}",
                data={"action": "update_signer", "signer": "John Doe"},
                follow_redirects=True)
    client.post(f"/returns/{rid}",
                data={"action": "update_dates",
                      "due_date": "2026-10-15", "extended_due_date": ""},
                follow_redirects=True)

    page = client.get(f"/returns/{rid}")
    assert b"<th>Change</th>" in page.data
    assert b"Signer" in page.data    # signer change labeled
    assert b"Due Dates" in page.data  # dates change labeled


def test_note_column_shows_only_status_notes(alice, client, db):
    """A signer edit's audit note must not surface in the list's Note
    column, which is scoped to status-change notes."""
    add_return(client, name="Note Scope Corp", signer="First Signer")
    rid = return_id(db, "Note Scope Corp")
    # Status change with a note...
    client.post(f"/returns/{rid}",
                data={"action": "change_status",
                      "new_status_id": str(status_id(db, "docs_waiting")),
                      "note": "waiting on Schedule K-1"},
                follow_redirects=True)
    # ...followed by a signer edit, whose note would otherwise win as
    # the most recent note-bearing history row.
    client.post(f"/returns/{rid}",
                data={"action": "update_signer", "signer": "Second Signer"},
                follow_redirects=True)

    page = client.get("/")
    assert b"waiting on Schedule K-1" in page.data
    assert b"Signer changed" not in page.data


# ------------------------------ CSV import ----------------------------------

def _upload(client, text, filename="import.csv"):
    return client.post("/returns/import-csv",
                       data={"csv_file": (io.BytesIO(text.encode("utf-8")),
                                          filename)},
                       follow_redirects=True)


CSV_OK = ("Return Name,Tax Year,Return Type,Due Date,Extended Due Date,Signer,Status\r\n"
          "Imported One,2026,1040,2026-04-15,,Jane Smith,\r\n"
          "Imported Two,2026,1065,,,,\r\n")


def test_import_requires_login(client):
    response = client.post("/returns/import-csv", data={})
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_import_requires_a_file(alice, client, db):
    response = client.post("/returns/import-csv", data={},
                           follow_redirects=True)
    assert b"choose a CSV file" in response.data


def test_import_missing_required_column_rejected_wholesale(alice, client, db):
    """A CSV lacking the Return Type column rejects the entire import."""
    response = _upload(client, "Return Name,Tax Year\r\nOnly Two Columns,2026\r\n")
    assert b"missing required column" in response.data
    count = db.execute("SELECT COUNT(*) AS n FROM tax_returns").fetchone()["n"]
    assert count == 0


def test_import_inserts_valid_rows(alice, client, db):
    response = _upload(client, CSV_OK)
    assert b"2 return(s) added" in response.data

    rows = db.execute("""SELECT return_name, signer, due_date, current_status_id
                         FROM tax_returns ORDER BY return_name""").fetchall()
    assert [r["return_name"] for r in rows] == ["Imported One", "Imported Two"]
    assert rows[0]["signer"] == "Jane Smith"
    assert rows[0]["due_date"] == "2026-04-15"
    # Blank status defaults to 'Not Started'.
    assert rows[0]["current_status_id"] == status_id(db, "not_started")


def test_import_status_by_code_and_label(alice, client, db):
    csv_text = ("Return Name,Tax Year,Return Type,Status\r\n"
                "By Code,2026,1040,with_preparer\r\n"
                "By Label,2026,1040,In Preparation\r\n")
    response = _upload(client, csv_text)
    assert b"2 return(s) added" in response.data

    for name in ("By Code", "By Label"):
        row = db.execute("""SELECT current_status_id FROM tax_returns
                            WHERE return_name = ?""", (name,)).fetchone()
        assert row["current_status_id"] == status_id(db, "with_preparer")


def test_import_unknown_status_rejects_row_only(alice, client, db):
    csv_text = ("Return Name,Tax Year,Return Type,Status\r\n"
                "Good Row,2026,1040,\r\n"
                "Bad Row,2026,1040,Warp Speed\r\n")
    response = _upload(client, csv_text)
    assert b"unknown status" in response.data

    names = [r["return_name"] for r in
             db.execute("SELECT return_name FROM tax_returns").fetchall()]
    assert names == ["Good Row"]


def test_import_duplicates_skipped(alice, client, db):
    add_return(client, name="Dup Corp", year="2026", rtype="1120")
    csv_text = ("Return Name,Tax Year,Return Type\r\n"
                "Dup Corp,2026,1120\r\n"
                "Fresh Corp,2026,1040\r\n")
    response = _upload(client, csv_text)
    assert b"duplicate" in response.data
    assert b"Fresh Corp" in response.data
    count = db.execute("SELECT COUNT(*) AS n FROM tax_returns").fetchone()["n"]
    assert count == 2


def test_import_invalid_year_rejects_row(alice, client, db):
    csv_text = ("Return Name,Tax Year,Return Type\r\n"
                "Bad Year,NaN,1040\r\n"
                "Good Year,2026,1040\r\n")
    response = _upload(client, csv_text)
    assert b"not a number" in response.data

    names = [r["return_name"] for r in
             db.execute("SELECT return_name FROM tax_returns").fetchall()]
    assert names == ["Good Year"]


def test_import_invalid_date_rejects_row(alice, client, db):
    csv_text = ("Return Name,Tax Year,Return Type,Due Date\r\n"
                "Bad Date,2026,1040,the fifteenth\r\n"
                "Good Date,2026,1040,04/15/2026\r\n")
    response = _upload(client, csv_text)
    assert b"invalid due date" in response.data

    row = db.execute("""SELECT due_date FROM tax_returns
                        WHERE return_name = 'Good Date'""").fetchone()
    # MM/DD/YYYY is accepted and normalized to ISO.
    assert row["due_date"] == "2026-04-15"


def test_import_missing_required_field_in_row(alice, client, db):
    csv_text = ("Return Name,Tax Year,Return Type\r\n"
                "No Year,,1040\r\n")
    response = _upload(client, csv_text)
    assert b"required" in response.data
    count = db.execute("SELECT COUNT(*) AS n FROM tax_returns").fetchone()["n"]
    assert count == 0


def test_import_header_aliasing(alice, client, db):
    """Alternate-but-recognizable headers map to the same fields, and
    case/punctuation differences are ignored."""
    csv_text = ("name,YEAR,Return_Type,signer\r\n"
                "Aliased Corp,2026,1120,Jane Smith\r\n")
    response = _upload(client, csv_text)
    assert b"1 return(s) added" in response.data

    row = db.execute("""SELECT return_name, signer FROM tax_returns""").fetchone()
    assert row["return_name"] == "Aliased Corp"
    assert row["signer"] == "Jane Smith"


def test_import_handles_utf8_bom(alice, client, db):
    """Excel prepends a BOM; it must not corrupt the first header."""
    csv_text = ("\ufeffReturn Name,Tax Year,Return Type\r\n"
                "BOM Corp,2026,1040\r\n")
    response = _upload(client, csv_text)
    assert b"missing required column" not in response.data
    assert b"1 return(s) added" in response.data


def test_import_writes_creation_history_entry(alice, client, db):
    _upload(client, CSV_OK)
    rid = return_id(db, "Imported One")
    history = db.execute("""SELECT change_type, note FROM status_history
                            WHERE return_id = ? ORDER BY id DESC LIMIT 1""",
                         (rid,)).fetchone()
    assert history["change_type"] == "status"
    assert "Imported from CSV" in history["note"]


def test_import_empty_file_rejected(alice, client, db):
    response = _upload(client, "\r\n\r\n")
    assert b"empty" in response.data
    count = db.execute("SELECT COUNT(*) AS n FROM tax_returns").fetchone()["n"]
    assert count == 0