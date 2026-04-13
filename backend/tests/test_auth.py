"""
Tests for POST /auth/login
"""
from tests.conftest import auth


def test_login_success(client, admin_user):
    res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["username"] == "admin"
    assert body["role"] == "admin"
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client, admin_user):
    res = client.post("/auth/login", json={"username": "admin", "password": "wrongpass"})
    assert res.status_code == 401


def test_login_nonexistent_user(client):
    res = client.post("/auth/login", json={"username": "ghost", "password": "anything"})
    assert res.status_code == 401


def test_login_returns_user_id_in_token(client, admin_user):
    """JWT payload must include user_id for permission checks in sheets endpoints."""
    import json, base64
    res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    token = res.json()["access_token"]
    # Decode payload segment without verifying signature
    padded = token.split(".")[1] + "=="
    payload = json.loads(base64.urlsafe_b64decode(padded))
    assert "user_id" in payload
    assert payload["user_id"] == admin_user["id"]


def test_protected_route_without_token(client):
    res = client.get("/sheets/")
    assert res.status_code == 401


def test_protected_route_with_invalid_token(client):
    res = client.get("/sheets/", headers=auth("not.a.valid.token"))
    assert res.status_code == 401
