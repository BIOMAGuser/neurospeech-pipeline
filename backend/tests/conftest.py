"""Shared fixtures for integration tests."""
import os
import sys
from pathlib import Path

import pytest
import requests

# Ensure tests/ is on sys.path so helpers.py can be imported
sys.path.insert(0, str(Path(__file__).parent))

from helpers import ADMIN_USER, ADMIN_PASS, STANDARD_USER, STANDARD_PASS, auth_headers

BASE_URL = os.environ.get("TEST_BASE_URL", "http://speechscribe-backend:8000")
FIXTURES = Path(__file__).parent / "fixtures"
TEST_OPENAI_API_KEY = os.environ.get("TEST_OPENAI_API_KEY")


def set_openai_key(base_url, token):
    """Store TEST_OPENAI_API_KEY in user DB. No-op if env var is unset."""
    if not TEST_OPENAI_API_KEY:
        return
    requests.put(
        f"{base_url}/user/openai-key",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json={"api_key": TEST_OPENAI_API_KEY},
    )


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def admin_token(base_url):
    """Authenticate as admin, set OpenAI key if provided via env, return JWT."""
    resp = requests.post(
        f"{base_url}/token",
        data={"username": ADMIN_USER, "password": ADMIN_PASS},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    token = resp.json()["access_token"]
    set_openai_key(base_url, token)
    return token


@pytest.fixture(scope="session")
def standard_token(base_url):
    """Authenticate as standard user and return JWT token."""
    resp = requests.post(
        f"{base_url}/token",
        data={"username": STANDARD_USER, "password": STANDARD_PASS},
    )
    assert resp.status_code == 200, f"Standard login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def fixtures_dir():
    return FIXTURES
