"""
Tests for GET /sheets/ and GET /sheets/{id}/data
Covers admin bypass and viewer permission filtering.
"""
from tests.conftest import auth, get_test_db


def test_admin_sees_all_sheets(client, admin_token, test_sheets):
    res = client.get("/sheets/", headers=auth(admin_token))
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_viewer_sees_no_sheets_by_default(client, viewer_token, test_sheets):
    res = client.get("/sheets/", headers=auth(viewer_token))
    assert res.status_code == 200
    assert res.json() == []


def test_viewer_sees_only_assigned_sheets(client, admin_token, viewer_token, viewer_user, test_sheets):
    sheet1_id = test_sheets["sheet1_id"]

    # Assign only sheet1 to viewer
    client.put(
        f"/admin/users/{viewer_user['id']}/sheets",
        json={"sheet_ids": [sheet1_id]},
        headers=auth(admin_token)
    )

    res = client.get("/sheets/", headers=auth(viewer_token))
    assert res.status_code == 200
    ids = [s["id"] for s in res.json()]
    assert sheet1_id in ids
    assert test_sheets["sheet2_id"] not in ids


def test_admin_can_access_any_sheet_data(client, admin_token, test_sheets):
    res = client.get(f"/sheets/{test_sheets['sheet1_id']}/data", headers=auth(admin_token))
    assert res.status_code == 200
    body = res.json()
    assert "rows" in body
    assert len(body["rows"]) == 1
    assert body["rows"][0]["Ticker"] == "AAPL"


def test_viewer_can_access_assigned_sheet_data(client, admin_token, viewer_token, viewer_user, test_sheets):
    sheet1_id = test_sheets["sheet1_id"]
    client.put(
        f"/admin/users/{viewer_user['id']}/sheets",
        json={"sheet_ids": [sheet1_id]},
        headers=auth(admin_token)
    )

    res = client.get(f"/sheets/{sheet1_id}/data", headers=auth(viewer_token))
    assert res.status_code == 200
    assert len(res.json()["rows"]) == 1


def test_viewer_blocked_from_unassigned_sheet_data(client, admin_token, viewer_token, viewer_user, test_sheets):
    # Assign only sheet1, try to access sheet2
    client.put(
        f"/admin/users/{viewer_user['id']}/sheets",
        json={"sheet_ids": [test_sheets["sheet1_id"]]},
        headers=auth(admin_token)
    )

    res = client.get(f"/sheets/{test_sheets['sheet2_id']}/data", headers=auth(viewer_token))
    assert res.status_code == 403


def test_sheet_data_returns_404_for_nonexistent_sheet(client, admin_token):
    res = client.get("/sheets/99999/data", headers=auth(admin_token))
    assert res.status_code == 404


def test_viewer_permissions_update_is_reflected_immediately(client, admin_token, viewer_token, viewer_user, test_sheets):
    """Revoking access takes effect on the next request."""
    sheet1_id = test_sheets["sheet1_id"]

    # Grant access
    client.put(
        f"/admin/users/{viewer_user['id']}/sheets",
        json={"sheet_ids": [sheet1_id]},
        headers=auth(admin_token)
    )
    assert client.get("/sheets/", headers=auth(viewer_token)).json() != []

    # Revoke access
    client.put(
        f"/admin/users/{viewer_user['id']}/sheets",
        json={"sheet_ids": []},
        headers=auth(admin_token)
    )
    assert client.get("/sheets/", headers=auth(viewer_token)).json() == []
