"""Login flow, access control, and the theme toggle."""


def test_index_requires_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_add_user_and_login(alice, client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Alice" in response.data


def test_theme_toggle_persists(alice, client):
    # Default is dark mode, so the offered action is switching to light.
    page = client.get("/")
    assert b"Light mode" in page.data

    client.get("/toggle-theme", follow_redirects=True)

    page = client.get("/")
    assert b"Dark mode" in page.data