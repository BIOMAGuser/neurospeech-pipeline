"""Transaction safety tests: verify atomic DB commits and rollback on failure."""
import time
from pathlib import Path

import pytest
import requests
from helpers import auth_headers

FIXTURES = Path(__file__).parent / "fixtures"


def _get_stats(base_url, token):
    resp = requests.get(f"{base_url}/stats", headers=auth_headers(token))
    assert resp.status_code == 200
    return resp.json()


def _skip_if_no_audio():
    path = FIXTURES / "veggie_answer.mp3"
    if not path.exists():
        pytest.skip("Audio fixture veggie_answer.mp3 not found")
    return path


class TestTransactionRollback:
    """Verify that failed requests don't leave orphaned DB records."""

    def test_invalid_task_type_no_orphans(self, base_url, admin_token):
        """An invalid taskType should roll back — no orphaned star schema records."""
        audio_path = _skip_if_no_audio()
        before = _get_stats(base_url, admin_token)

        unique_id = f"orphan_test_{int(time.time())}"
        with open(audio_path, "rb") as f:
            resp = requests.post(
                f"{base_url}/analyze",
                headers=auth_headers(admin_token),
                files={"audio": ("test.mp3", f, "audio/mpeg")},
                data={
                    "taskType": "nonexistent_task",
                    "attemptId": unique_id,
                    "patient_id": f"ORPHAN-{unique_id}",
                    "test_date": "2026-01-01",
                    "session_analysis_id": unique_id,
                    "save_to_database": "true",
                },
            )

        assert resp.status_code in (400, 422, 500), f"Expected failure, got {resp.status_code}"

        after = _get_stats(base_url, admin_token)
        assert after["patients"] == before["patients"], "Orphaned patient created in PATIENT_DIMENSION"
        assert after["analyses"] == before["analyses"], "Orphaned visit created in VISIT_DIMENSION"
        assert after["trials"] == before["trials"], "Orphaned observations created in OBSERVATION_FACT"

    def test_save_false_no_records(self, base_url, admin_token):
        """When save_to_database=false, no star schema records should be created."""
        audio_path = _skip_if_no_audio()
        before = _get_stats(base_url, admin_token)

        unique_id = f"nosave_test_{int(time.time())}"
        with open(audio_path, "rb") as f:
            resp = requests.post(
                f"{base_url}/analyze",
                headers=auth_headers(admin_token),
                files={"audio": ("test.mp3", f, "audio/mpeg")},
                data={
                    "taskType": "veggie",
                    "attemptId": unique_id,
                    "patient_id": f"NOSAVE-{unique_id}",
                    "session_analysis_id": unique_id,
                    "save_to_database": "false",
                },
            )

        if resp.status_code == 500 and "invalid_api_key" in resp.text:
            pytest.skip("OpenAI key is placeholder/invalid")

        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_id" not in data or data.get("analysis_id") is None, \
            "analysis_id should not be present when save_to_database=false"

        after = _get_stats(base_url, admin_token)
        assert after["patients"] == before["patients"]
        assert after["analyses"] == before["analyses"]
        assert after["trials"] == before["trials"]

    def test_missing_patient_id_returns_422(self, base_url, admin_token):
        """save_to_database=true without patient_id should return 422."""
        audio_path = _skip_if_no_audio()
        with open(audio_path, "rb") as f:
            resp = requests.post(
                f"{base_url}/analyze",
                headers=auth_headers(admin_token),
                files={"audio": ("test.mp3", f, "audio/mpeg")},
                data={
                    "taskType": "veggie",
                    "attemptId": "test_no_patient",
                    "save_to_database": "true",
                    # patient_id intentionally omitted
                },
            )
        assert resp.status_code == 422

    def test_invalid_date_returns_422(self, base_url, admin_token):
        """Invalid test_date format should return 422."""
        audio_path = _skip_if_no_audio()
        with open(audio_path, "rb") as f:
            resp = requests.post(
                f"{base_url}/analyze",
                headers=auth_headers(admin_token),
                files={"audio": ("test.mp3", f, "audio/mpeg")},
                data={
                    "taskType": "veggie",
                    "attemptId": "test_bad_date",
                    "patient_id": "BAD-DATE-TEST",
                    "test_date": "not-a-date",
                    "save_to_database": "true",
                },
            )
        assert resp.status_code == 422
