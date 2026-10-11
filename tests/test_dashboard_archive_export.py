"""Dashboard counts, archiving, and CSV export."""
from tests.conftest import add_return, return_id, status_id


def test_dashboard_hides_zero_counts(alice, client):
    add_return(client)  # one return at 'Not Started'
    response = client.get("/")
    # Exactly one status card: the untouched statuses must not phantom-count.
    assert response.data.count(b'class="status-card') == 1
    assert b"Not Started" in response.data


def test_dashboard_counts_active_only(alice, client, db):
    add_return(client, name="Active One")
    add_return(client, name="Done One", rtype="990")
    rid_done = return_id(db, "Done One")
    complete = status_id(db, "complete")

    client.post(f"/returns/{rid_done}",
                data={"action": "change_status",
                      "new_status_id": str(complete)},
                follow_redirects=True)
    client.post(f"/returns/{rid_done}/archive",
                data={"archive_action": "archive"},
                follow_redirects=True)

    response = client.get("/")
    assert b"Done One" not in response.data          # archived hidden
    assert response.data.count(b'class="status-card') == 1  # only active counted


def test_archive_then_restore(alice, client, db):
    add_return(client)
    rid = return_id(db)

    client.post(f"/returns/{rid}/archive",
                data={"archive_action": "archive"},
                follow_redirects=True)
    assert b"Acme Corp" not in client.get("/").data

    archived_view = client.get("/?archived=1")
    assert b"Acme Corp" in archived_view.data

    client.post(f"/returns/{rid}/archive",
                data={"archive_action": "unarchive"},
                follow_redirects=True)
    assert b"Acme Corp" in client.get("/").data


def test_csv_export_contains_rows(alice, client):
    add_return(client, name="Export Corp", year="2026", rtype="1120",
               due="2026-04-15")
    response = client.get("/returns/export-csv")

    assert response.status_code == 200
    assert b"Return Name" in response.data
    assert b"Export Corp" in response.data
    assert response.headers["Content-Type"].startswith("text/csv")


def test_csv_export_excludes_archived(alice, client, db):
    add_return(client, name="Keep Corp")
    add_return(client, name="Gone Corp", rtype="1040")
    rid = return_id(db, "Gone Corp")
    client.post(f"/returns/{rid}/archive",
                data={"archive_action": "archive"},
                follow_redirects=True)

    response = client.get("/returns/export-csv")
    assert b"Keep Corp" in response.data
    assert b"Gone Corp" not in response.data