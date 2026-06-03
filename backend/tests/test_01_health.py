"""Basic health, status, and star schema verification tests."""
import requests
from helpers import auth_headers


def test_health(base_url):
    resp = requests.get(f"{base_url}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_stats(base_url, admin_token):
    resp = requests.get(f"{base_url}/stats", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "patients" in data
    assert "analyses" in data
    assert "trials" in data
    assert isinstance(data["patients"], int)
    assert isinstance(data["analyses"], int)
    assert isinstance(data["trials"], int)


def test_stats_requires_auth(base_url):
    resp = requests.get(f"{base_url}/stats")
    assert resp.status_code == 401


class TestStarSchemaReady:
    """Verify the star schema tables and seed data exist after startup."""

    def test_star_views_queryable(self, base_url, admin_token):
        """The debug endpoint for star schema views should work."""
        resp = requests.get(
            f"{base_url}/debug/patient_analysis_trials",
            headers=auth_headers(admin_token),
        )
        # 404 = DEBUG mode off (expected in non-debug environments), 200 = works
        assert resp.status_code in (200, 404), (
            f"Star schema view not queryable: {resp.status_code} {resp.text}"
        )
        if resp.status_code == 200:
            assert isinstance(resp.json(), list)

    def test_debug_patients_works(self, base_url, admin_token):
        """Debug patients endpoint reads from PATIENT_DIMENSION."""
        resp = requests.get(
            f"{base_url}/debug/patients",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, list)
            if data:
                assert "id" in data[0]
                assert "patient_id" in data[0]
