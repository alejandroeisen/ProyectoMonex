"""
Tests for /admin/* endpoints.
Covers user management and sheet permission assignment.
"""
from tests.conftest import auth


# ── Access control ────────────────────────────────────────────────────────────

def test_viewer_cannot_access_admin_endpoints(client, viewer_token):
    assert client.get("/admin/users", headers=auth(viewer_token)).status_code == 403
    assert client.post("/admin/users", json={}, headers=auth(viewer_token)).status_code == 403


def test_unauthenticated_cannot_access_admin_endpoints(client):
    assert client.get("/admin/users").status_code == 401


# ── List users ────────────────────────────────────────────────────────────────

def test_list_users_returns_all_users(client, admin_token, admin_user, viewer_user):
    res = client.get("/admin/users", headers=auth(admin_token))
    assert res.status_code == 200
    usernames = [u["username"] for u in res.json()]
    assert "admin" in usernames
    assert "viewer" in usernames


def test_list_users_does_not_expose_password_hash(client, admin_token, admin_user):
    res = client.get("/admin/users", headers=auth(admin_token))
    for user in res.json():
        assert "password_hash" not in user


def test_list_users_includes_sheet_ids(client, admin_token, admin_user):
    res = client.get("/admin/users", headers=auth(admin_token))
    for user in res.json():
        assert "sheet_ids" in user
        assert isinstance(user["sheet_ids"], list)


# ── Create user ───────────────────────────────────────────────────────────────

def test_create_user_success(client, admin_token, admin_user):
    res = client.post(
        "/admin/users",
        json={"username": "newuser", "password": "pass123", "role": "viewer"},
        headers=auth(admin_token)
    )
    assert res.status_code == 201
    body = res.json()
    assert body["username"] == "newuser"
    assert body["role"] == "viewer"
    assert "password_hash" not in body


def test_create_user_defaults_to_viewer_role(client, admin_token, admin_user):
    res = client.post(
        "/admin/users",
        json={"username": "newuser", "password": "pass123"},
        headers=auth(admin_token)
    )
    assert res.status_code == 201
    assert res.json()["role"] == "viewer"


def test_create_user_duplicate_username(client, admin_token, admin_user):
    client.post(
        "/admin/users",
        json={"username": "newuser", "password": "pass123"},
        headers=auth(admin_token)
    )
    res = client.post(
        "/admin/users",
        json={"username": "newuser", "password": "otherpass"},
        headers=auth(admin_token)
    )
    assert res.status_code == 400


def test_new_user_can_login(client, admin_token, admin_user):
    client.post(
        "/admin/users",
        json={"username": "newuser", "password": "pass123"},
        headers=auth(admin_token)
    )
    res = client.post("/auth/login", json={"username": "newuser", "password": "pass123"})
    assert res.status_code == 200
    assert "access_token" in res.json()


# ── Delete user ───────────────────────────────────────────────────────────────

def test_delete_user_success(client, admin_token, admin_user, viewer_user):
    res = client.delete(f"/admin/users/{viewer_user['id']}", headers=auth(admin_token))
    assert res.status_code == 204

    # Confirm gone from list
    users = client.get("/admin/users", headers=auth(admin_token)).json()
    assert not any(u["id"] == viewer_user["id"] for u in users)


def test_delete_user_cascades_sheet_permissions(client, admin_token, admin_user, viewer_user, test_sheets):
    # Assign sheets then delete the user — user_sheets rows should be gone
    client.put(
        f"/admin/users/{viewer_user['id']}/sheets",
        json={"sheet_ids": [test_sheets["sheet1_id"]]},
        headers=auth(admin_token)
    )
    client.delete(f"/admin/users/{viewer_user['id']}", headers=auth(admin_token))

    # Re-create same user and check they have no sheets
    client.post(
        "/admin/users",
        json={"username": "viewer", "password": "viewer123"},
        headers=auth(admin_token)
    )
    users = client.get("/admin/users", headers=auth(admin_token)).json()
    viewer = next(u for u in users if u["username"] == "viewer")
    assert viewer["sheet_ids"] == []


def test_delete_self_is_blocked(client, admin_token, admin_user):
    res = client.delete(f"/admin/users/{admin_user['id']}", headers=auth(admin_token))
    assert res.status_code == 400


def test_delete_nonexistent_user(client, admin_token, admin_user):
    res = client.delete("/admin/users/99999", headers=auth(admin_token))
    assert res.status_code == 404


# ── Update sheet permissions ──────────────────────────────────────────────────

def test_update_sheets_assigns_correctly(client, admin_token, admin_user, viewer_user, test_sheets):
    res = client.put(
        f"/admin/users/{viewer_user['id']}/sheets",
        json={"sheet_ids": [test_sheets["sheet1_id"], test_sheets["sheet2_id"]]},
        headers=auth(admin_token)
    )
    assert res.status_code == 200
    assert set(res.json()["sheet_ids"]) == {test_sheets["sheet1_id"], test_sheets["sheet2_id"]}


def test_update_sheets_replaces_previous_assignments(client, admin_token, admin_user, viewer_user, test_sheets):
    # Assign sheet1, then replace with sheet2 only
    client.put(
        f"/admin/users/{viewer_user['id']}/sheets",
        json={"sheet_ids": [test_sheets["sheet1_id"]]},
        headers=auth(admin_token)
    )
    client.put(
        f"/admin/users/{viewer_user['id']}/sheets",
        json={"sheet_ids": [test_sheets["sheet2_id"]]},
        headers=auth(admin_token)
    )
    users = client.get("/admin/users", headers=auth(admin_token)).json()
    viewer = next(u for u in users if u["id"] == viewer_user["id"])
    assert viewer["sheet_ids"] == [test_sheets["sheet2_id"]]


def test_update_sheets_with_empty_list_revokes_all(client, admin_token, admin_user, viewer_user, test_sheets):
    client.put(
        f"/admin/users/{viewer_user['id']}/sheets",
        json={"sheet_ids": [test_sheets["sheet1_id"]]},
        headers=auth(admin_token)
    )
    client.put(
        f"/admin/users/{viewer_user['id']}/sheets",
        json={"sheet_ids": []},
        headers=auth(admin_token)
    )
    users = client.get("/admin/users", headers=auth(admin_token)).json()
    viewer = next(u for u in users if u["id"] == viewer_user["id"])
    assert viewer["sheet_ids"] == []


def test_update_sheets_nonexistent_user(client, admin_token, admin_user, test_sheets):
    res = client.put(
        "/admin/users/99999/sheets",
        json={"sheet_ids": [test_sheets["sheet1_id"]]},
        headers=auth(admin_token)
    )
    assert res.status_code == 404
