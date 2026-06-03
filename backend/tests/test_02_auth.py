"""Authentication and user management tests."""
import requests
from helpers import auth_headers, ADMIN_USER, STANDARD_USER


def test_login_admin(base_url):
    resp = requests.post(
        f"{base_url}/token",
        data={"username": "testuser", "password": "testpassword"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_standard_user(base_url):
    resp = requests.post(
        f"{base_url}/token",
        data={"username": "arzt", "password": "arzt1234"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_invalid_password(base_url):
    resp = requests.post(
        f"{base_url}/token",
        data={"username": "testuser", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_nonexistent_user(base_url):
    resp = requests.post(
        f"{base_url}/token",
        data={"username": "nobody", "password": "nopass"},
    )
    assert resp.status_code == 401


def test_user_me_admin(base_url, admin_token):
    resp = requests.get(f"{base_url}/user/me", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == ADMIN_USER
    assert data["is_active"] is True
    assert "has_openai_key" in data
    assert "created_at" in data


def test_user_me_standard(base_url, standard_token):
    resp = requests.get(f"{base_url}/user/me", headers=auth_headers(standard_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == STANDARD_USER
    assert data["is_active"] is True


def test_user_me_requires_auth(base_url):
    resp = requests.get(f"{base_url}/user/me")
    assert resp.status_code == 401
