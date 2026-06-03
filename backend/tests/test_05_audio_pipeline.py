"""Full audio pipeline tests: gTTS audio → Whisper → Analysis → Star Schema storage.
Requires:
  - Valid OpenAI API key (for Whisper + GPT)
  - Audio fixtures generated via: python tests/generate_audio_fixtures.py
"""
from pathlib import Path

import pytest
import requests
from helpers import auth_headers

FIXTURES = Path(__file__).parent / "fixtures"

TASKS = [
    ("veggie", "veggie_answer.mp3"),
    ("saying", "saying_answer.mp3"),
    ("picture", "picture_answer.mp3"),
]


def _skip_if_no_audio(filename):
    path = FIXTURES / filename
    if not path.exists():
        pytest.skip(f"Audio fixture {filename} not found — run: python tests/generate_audio_fixtures.py")
    return path


@pytest.fixture(scope="module")
def session_analysis_id():
    import time
    return f"test_session_{int(time.time())}"


@pytest.mark.parametrize("task_type,audio_file", TASKS)
def test_analyze_audio(base_url, admin_token, task_type, audio_file, session_analysis_id):
    """Audio upload → Whisper → analysis → star schema DB save."""
    audio_path = _skip_if_no_audio(audio_file)

    with open(audio_path, "rb") as f:
        resp = requests.post(
            f"{base_url}/analyze",
            headers=auth_headers(admin_token),
            files={"audio": (audio_file, f, "audio/mpeg")},
            data={
                "taskType": task_type,
                "attemptId": f"test_{task_type}_audio_001",
                "duration_seconds": "10.0",
                "patient_id": "TEST-INTEG-001",
                "test_date": "2026-03-15",
                "group": "Kontrolle",
                "session_analysis_id": session_analysis_id,
                "save_to_database": "true",
            },
        )

    if resp.status_code == 500 and "invalid_api_key" in resp.text:
        pytest.skip(f"[{task_type}] Whisper failed — OpenAI key is placeholder/invalid")

    assert resp.status_code == 200, f"[{task_type}] Failed: {resp.text}"
    data = resp.json()

    # Basic response structure
    assert data["task"] == task_type
    assert "transcript" in data
    assert "metrics" in data
    assert len(data["transcript"]) > 0, f"[{task_type}] Empty transcript"

    # Star schema IDs should be present (encounter_num used as analysis_id)
    assert "patient_id" in data
    assert "analysis_id" in data

    m = data["metrics"]
    print(f"\n  [{task_type.upper()}] transcript: {data['transcript'][:80]}...")
    print(f"  [{task_type.upper()}] metrics: {m}")

    # Task-specific assertions
    if task_type == "veggie":
        assert "points" in m
        assert "correct_words" in m
    elif task_type == "saying":
        assert "points" in m
        assert "filler_word_count" in m
    elif task_type == "picture":
        assert "pic_points" in m
        assert "sentence_count" in m
        assert "ttr" in m


def test_db_persistence(base_url, admin_token):
    """Verify the test patient, visit, and observations were saved in star schema."""
    resp = requests.get(f"{base_url}/patients", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    patients = resp.json()

    test_patient = next((p for p in patients if p["patient_id"] == "TEST-INTEG-001"), None)
    if test_patient is None:
        pytest.skip("Test patient not found — audio tests were skipped")

    assert test_patient["analysis_count"] >= 1

    # Check visits (analyses) for this patient
    resp = requests.get(
        f"{base_url}/patients/{test_patient['id']}/analyses",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    analyses = resp.json()
    assert len(analyses) >= 1

    analysis = analyses[0]
    assert "session_analysis_id" in analysis
    assert "trial_count" in analysis

    # Check visit detail with reconstructed trials
    resp = requests.get(
        f"{base_url}/analyses/{analysis['id']}",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    detail = resp.json()
    assert "trials" in detail
    assert len(detail["trials"]) >= 1

    # Verify trial structure (reconstructed from EAV observations)
    for trial in detail["trials"]:
        assert "task" in trial
        assert trial["task"] in ("veggie", "saying", "picture")
        assert "metrics" in trial
        if trial.get("transcript"):
            assert len(trial["transcript"]) > 0
            print(f"\n  DB Trial [{trial['task']}]: {trial['transcript'][:60]}... points={trial.get('points')}")


def test_analysis_detail_has_session_metadata(base_url, admin_token):
    """Verify that session-level metadata (moca_score, group) is returned."""
    resp = requests.get(f"{base_url}/patients", headers=auth_headers(admin_token))
    patients = resp.json()
    test_patient = next((p for p in patients if p["patient_id"] == "TEST-INTEG-001"), None)
    if test_patient is None:
        pytest.skip("Test patient not found")

    resp = requests.get(
        f"{base_url}/patients/{test_patient['id']}/analyses",
        headers=auth_headers(admin_token),
    )
    analyses = resp.json()
    if not analyses:
        pytest.skip("No analyses found")

    detail_resp = requests.get(
        f"{base_url}/analyses/{analyses[0]['id']}",
        headers=auth_headers(admin_token),
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    # Session-level fields should be present
    assert "moca_score" in detail
    assert "group" in detail
    assert "session_analysis_id" in detail
    assert "patient_id" in detail
    assert detail["patient_id"] == "TEST-INTEG-001"
