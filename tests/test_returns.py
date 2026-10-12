"""Return lifecycle: creation, validation, status changes, history."""
import re

from tests.conftest import add_return, return_id, status_id


def test_all_constants_statuses_seeded(alice, db):
    """Drift guard: every status in constants.py must exist in the DB."""
    from constants import STATUSES
    for code, label, _order in STATUSES:
        assert status_id(db, code) is not None, f"missing seeded status: {code}"


def test_create_return_shows_in_list(alice, client):
    response = add_return(client, name="Beta LLC")
    assert response.status_code == 200
    assert b"Beta LLC" in response.data


def test_duplicate_return_rejected(alice, client, db):
    add_return(client, name="Acme Corp", year="2026", rtype="1120")
    add_return(client, name="Acme Corp", year="2026", rtype="1120")
    count = db.execute("SELECT COUNT(*) AS n FROM tax_returns").fetchone()["n"]
    assert count == 1


def test_same_name_different_year_allowed(alice, client, db):
    add_return(client, name="Acme Corp", year="2025")
    add_return(client, name="Acme Corp", year="2026")
    count = db.execute("SELECT COUNT(*) AS n FROM tax_returns").fetchone()["n"]
    assert count == 2


def test_missing_fields_are_rejected(alice, client, db):
    response = client.post("/returns/new",
                           data={"return_name": "", "tax_year": "2026",
                                 "return_type": "1040"},
                           follow_redirects=True)
    assert b"required" in response.data
    count = db.execute("SELECT COUNT(*) AS n FROM tax_returns").fetchone()["n"]
    assert count == 0


def test_status_change_logs_history(alice, client, db):
    add_return(client)
    rid = return_id(db)
    new_status = status_id(db, "docs_waiting")

    client.post(f"/returns/{rid}",
                data={"action": "change_status",
                      "new_status_id": str(new_status),
                      "note": "waiting on K-1"},
                follow_redirects=True)

    row = db.execute("""SELECT current_status_id FROM tax_returns
                        WHERE id = ?""", (rid,)).fetchone()
    assert row["current_status_id"] == new_status

    history = db.execute("""SELECT note, changed_by FROM status_history
                            WHERE return_id = ? ORDER BY id DESC LIMIT 1""",
                         (rid,)).fetchone()
    assert history["note"] == "waiting on K-1"
    assert history["changed_by"] == alice


def test_detail_preselects_current_status(alice, client, db):
    """The dropdown defaults to the return's current status, so a
    note-only update doesn't require re-picking the status."""
    add_return(client)
    rid = return_id(db)
    target = status_id(db, "with_reviewer")

    client.post(f"/returns/{rid}",
                data={"action": "change_status",
                      "new_status_id": str(target)},
                follow_redirects=True)

    page = client.get(f"/returns/{rid}")
    assert re.search(rb'<option value="%d"\s+selected' % target, page.data)


def test_note_only_update_records_history_entry(alice, client, db):
    """Submitting the pre-selected status with just a note logs a
    same-status history entry carrying the note."""
    add_return(client)
    rid = return_id(db)
    current = status_id(db, "not_started")

    client.post(f"/returns/{rid}",
                data={"action": "change_status",
                      "new_status_id": str(current),
                      "note": "phone call re: missing W-2"},
                follow_redirects=True)

    history = db.execute("""SELECT old_status_id, new_status_id, note
                            FROM status_history
                            WHERE return_id = ? ORDER BY id DESC LIMIT 1""",
                         (rid,)).fetchone()
    assert history["old_status_id"] == current
    assert history["new_status_id"] == current
    assert history["note"] == "phone call re: missing W-2"


def test_backward_status_moves_allowed(alice, client, db):
    add_return(client)
    rid = return_id(db)
    with_reviewer = status_id(db, "with_reviewer")
    waiting = status_id(db, "docs_waiting")

    client.post(f"/returns/{rid}",
                data={"action": "change_status",
                      "new_status_id": str(with_reviewer)},
                follow_redirects=True)
    response = client.post(f"/returns/{rid}",
                           data={"action": "change_status",
                                 "new_status_id": str(waiting)},
                           follow_redirects=True)

    assert response.status_code == 200
    row = db.execute("SELECT current_status_id FROM tax_returns WHERE id = ?",
                     (rid,)).fetchone()
    assert row["current_status_id"] == waiting


def test_invalid_status_id_rejected(alice, client, db):
    add_return(client)
    rid = return_id(db)
    response = client.post(f"/returns/{rid}",
                data={"action": "change_status",
                      "new_status_id": "9999"},
                follow_redirects=True)
    assert b"Invalid status" in response.data


def test_overdue_return_flagged(alice, client):
    add_return(client, name="Past Due Inc", due="2020-01-01")
    response = client.get("/")
    assert b"OVERDUE" in response.data


def test_type_filter(alice, client):
    add_return(client, name="Personal One", rtype="1040")
    add_return(client, name="Partnership Two", rtype="1065")
    response = client.get("/?type=1065")
    assert b"Partnership Two" in response.data
    assert b"Personal One" not in response.data


def test_new_return_has_styled_cancel_button(alice, client):
    """Smoke test: the Cancel link carries the btn-cancel styling hook."""
    page = client.get("/returns/new")
    assert b"btn-cancel" in page.data


def test_new_return_form_has_single_other_option(alice, client):
    """Guards against the duplicate 'Other' option (one from the
    RETURN_TYPES loop, one hardcoded in the template). Requires the
    extra <option>Other</option> line to have been removed from
    new_return.html."""
    page = client.get("/returns/new")
    assert page.data.count(b"<option>Other</option>") == 1