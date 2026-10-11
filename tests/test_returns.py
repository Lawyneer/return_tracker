"""Return lifecycle: creation, validation, status changes, history."""
from tests.conftest import add_return, return_id, status_id


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
    new_status = status_id(db, "waiting_on_documents")

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


def test_backward_status_moves_allowed(alice, client, db):
    add_return(client)
    rid = return_id(db)
    with_reviewer = status_id(db, "with_reviewer")
    waiting = status_id(db, "waiting_on_documents")

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