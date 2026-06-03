"""Shared test helpers."""
import os

ADMIN_USER = os.getenv("ADMIN_USERNAME", "testuser")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "testpassword")
STANDARD_USER = os.getenv("TEST_USERNAME", "arzt")
STANDARD_PASS = os.getenv("TEST_PASSWORD", "arzt1234")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
