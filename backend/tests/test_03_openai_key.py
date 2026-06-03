"""OpenAI key management endpoint tests."""
import requests
from conftest import set_openai_key
from helpers import auth_headers


def test_key_status_initial(base_url, admin_token):
    """Seeded users have no key initially — must be set via settings."""
    resp = requests.get(
        f"{base_url}/user/openai-key/status",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "has_key" in data
    assert isinstance(data["has_key"], bool)


def test_set_key(base_url, admin_token):
    """Store a new key."""
    resp = requests.put(
        f"{base_url}/user/openai-key",
        headers={**auth_headers(admin_token), "Content-Type": "application/json"},
        json={"api_key": "sk-test-integration-key-12345"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Verify status shows key is stored
    status = requests.get(
        f"{base_url}/user/openai-key/status",
        headers=auth_headers(admin_token),
    )
    assert status.json()["has_key"] is True


def test_delete_key(base_url, admin_token):
    """Delete stored key."""
    resp = requests.delete(
        f"{base_url}/user/openai-key",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Verify status shows no key
    status = requests.get(
        f"{base_url}/user/openai-key/status",
        headers=auth_headers(admin_token),
    )
    assert status.json()["has_key"] is False


def test_delete_confirms_no_key(base_url, admin_token):
    """After deleting user key, no key is configured."""
    status = requests.get(
        f"{base_url}/user/openai-key/status",
        headers=auth_headers(admin_token),
    )
    # Key was deleted in previous test — should be False
    assert status.json()["has_key"] is False


def test_key_requires_auth(base_url):
    resp = requests.get(f"{base_url}/user/openai-key/status")
    assert resp.status_code == 401

    resp = requests.put(
        f"{base_url}/user/openai-key",
        json={"api_key": "sk-nope"},
    )
    assert resp.status_code == 401

    resp = requests.delete(f"{base_url}/user/openai-key")
    assert resp.status_code == 401


def test_restore_key(base_url, admin_token):
    """Restore the OpenAI key for subsequent test modules."""
    set_openai_key(base_url, admin_token)
