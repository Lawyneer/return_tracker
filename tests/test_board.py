"""Kanban board: column grouping, counts, filters, and archive scope."""
import re

from tests.conftest import add_return, return_id, status_id

COLUMN_TITLES = ["Not Started", "Preparing", "In Review", "Completed"]


def _columns(page):
    """Split a rendered board into [(title_bytes, section_html), ...]."""
    sections = re.findall(
        rb'<section class="kanban-col">(.*?)</section>',
        page.data, re.S)
    result = []
    for section in sections:
        title = re.search(rb'kanban-col-title">([^<]+)</span>', section)
        result.append((title.group(1), section))
    return result


def _counts(page):
    """Column title -> card count, as rendered in the header badges."""
    return {title: int(re.search(rb'kanban-count">(\d+)<', section).group(1))
            for title, section in _columns(page)}


def _move(client, db, rid, code, note=""):
    """Change a return's status through the web form."""
    client.post(f"/returns/{rid}",
                data={"action": "change_status",
                      "new_status_id": str(status_id(db, code)),
                      "note": note},
                follow_redirects=True)


def test_board_requires_login(client):
    response = client.get("/board")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_board_shows_four_empty_columns(alice, client):
    page = client.get("/board")
    counts = _counts(page)
    assert list(counts) == [c.encode() for c in COLUMN_TITLES]
    assert all(v == 0 for v in counts.values())
    assert page.data.count(b"kanban-empty") == 4


def test_new_return_starts_in_not_started_column(alice, client):
    add_return(client)
    page = client.get("/board")
    counts = _counts(page)
    assert counts[b"Not Started"] == 1
    assert counts[b"Preparing"] == 0
    assert counts[b"In Review"] == 0
    assert counts[b"Completed"] == 0
    assert b"Acme Corp" in page.data


def test_board_buckets_statuses_per_column_spec(alice, client, db):
    """Exercises the full column mapping: every status code in
    constants.py must land in the KANBAN_COLUMNS bucket that claims it."""
    cases = [
        ("Alpha",   "not_started",        "Not Started"),
        ("Bravo",   "docs_requested",     "Not Started"),
        ("Charlie", "with_preparer",      "Preparing"),
        ("Delta",   "docs_waiting",       "Preparing"),
        ("Echo",    "with_reviewer",      "In Review"),
        ("Foxtrot", "with_or",            "In Review"),
        ("Golf",    "out_for_signatures", "Completed"),
        ("Hotel",   "eforms_received",    "Completed"),
        ("India",   "complete",           "Completed"),
    ]
    for name, code, _column in cases:
        add_return(client, name=name, rtype="1040")
        rid = return_id(db, name)
        if code != "not_started":
            _move(client, db, rid, code)

    page = client.get("/board")
    sections = dict(_columns(page))
    for name, code, column in cases:
        assert name.encode() in sections[column.encode()], (
            f"{name} (status '{code}') should appear in the {column} column")

    counts = _counts(page)
    assert counts == {
        b"Not Started": 2, b"Preparing": 2,
        b"In Review": 2, b"Completed": 3,
    }


def test_board_hides_archived_returns(alice, client, db):
    add_return(client, name="Kept Corp")
    add_return(client, name="Buried Corp", rtype="990")
    rid = return_id(db, "Buried Corp")
    client.post(f"/returns/{rid}/archive",
                data={"archive_action": "archive"}, follow_redirects=True)

    page = client.get("/board")
    assert b"Kept Corp" in page.data
    assert b"Buried Corp" not in page.data

    archived_page = client.get("/board?archived=1")
    assert b"Buried Corp" in archived_page.data
    assert b"Kept Corp" not in archived_page.data


def test_board_type_filter_and_name_search(alice, client):
    add_return(client, name="Solo 1040", rtype="1040")
    add_return(client, name="Group 1065", rtype="1065")

    page = client.get("/board?type=1065")
    assert b"Group 1065" in page.data
    assert b"Solo 1040" not in page.data

    page = client.get("/board?q=solo")
    assert b"Solo 1040" in page.data
    assert b"Group 1065" not in page.data