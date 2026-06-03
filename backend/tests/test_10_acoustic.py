"""
Acoustic feature endpoint tests.

These exercise POST/GET /trials/{id}/acoustic. A real trial with audio is
required for the smoke test — relies on test_05_audio_pipeline.py having
created the TEST-INTEG-001 patient. Tests skip gracefully if not.
"""
from pathlib import Path

import pytest
import requests
from helpers import auth_headers

FIXTURES = Path(__file__).parent / "fixtures"


def _find_trial_with_audio(base_url: str, token: str) -> int | None:
    """Return the OBSERVATION_ID of any trial that has an audio file, or None."""
    resp = requests.get(f"{base_url}/patients", headers=auth_headers(token))
    if resp.status_code != 200:
        return None

    for patient in resp.json():
        analyses_resp = requests.get(
            f"{base_url}/patients/{patient['id']}/analyses",
            headers=auth_headers(token),
        )
        if analyses_resp.status_code != 200:
            continue
        for analysis in analyses_resp.json():
            detail_resp = requests.get(
                f"{base_url}/analyses/{analysis['id']}",
                headers=auth_headers(token),
            )
            if detail_resp.status_code != 200:
                continue
            for trial in detail_resp.json().get("trials", []):
                if trial.get("audio_uuid") and trial.get("id"):
                    return trial["id"]
    return None


@pytest.fixture(scope="module")
def trial_id(base_url, admin_token):
    """Find a trial with audio. Skip the whole module if none exists."""
    tid = _find_trial_with_audio(base_url, admin_token)
    if tid is None:
        pytest.skip(
            "No trial with audio found — run test_05_audio_pipeline.py first "
            "(requires a valid OpenAI API key)."
        )
    return tid


def test_acoustic_unauthorized(base_url):
    """No token → 401."""
    resp = requests.post(f"{base_url}/trials/1/acoustic")
    assert resp.status_code == 401


def test_acoustic_invalid_observation_id(base_url, admin_token):
    """Non-existent observation_id → 404."""
    resp = requests.post(
        f"{base_url}/trials/999999999/acoustic",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


def test_acoustic_compute_smoke(base_url, admin_token, trial_id):
    """POST should compute and persist a substantial feature set."""
    resp = requests.post(
        f"{base_url}/trials/{trial_id}/acoustic",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["observation_id"] == trial_id
    assert data["task"] in ("veggie", "saying", "picture")
    assert data["audio_uuid"]
    assert data["computation_ms"] >= 0

    features = data["features"]
    # Expect ≥30 of the 39 features to extract on synthetic gTTS audio.
    # Some (e.g. higher-order MFCCs or jitter on very short samples) may fail.
    numeric_count = sum(1 for v in features.values() if isinstance(v, (int, float)))
    assert numeric_count >= 30, f"Only {numeric_count} numeric features: {features}"

    # Spot-check key feature names exist
    assert "f0_mean_hz" in features
    assert "jitter_local" in features
    assert "shimmer_local" in features
    assert "mfcc_1_mean" in features
    assert "hnr_mean_db" in features


def test_acoustic_get_after_post(base_url, admin_token, trial_id):
    """GET should return the same feature set persisted by the prior POST."""
    resp = requests.get(
        f"{base_url}/trials/{trial_id}/acoustic",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["observation_id"] == trial_id
    assert data["feature_count"] >= 30


def test_acoustic_idempotent(base_url, admin_token, trial_id):
    """Calling POST twice should yield the same feature_count (overwrite, not append)."""
    r1 = requests.post(
        f"{base_url}/trials/{trial_id}/acoustic",
        headers=auth_headers(admin_token),
    )
    r2 = requests.post(
        f"{base_url}/trials/{trial_id}/acoustic",
        headers=auth_headers(admin_token),
    )
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["feature_count"] == r2.json()["feature_count"]

    # And the feature *values* should be identical (deterministic extraction)
    f1 = r1.json()["features"]
    f2 = r2.json()["features"]
    for k, v in f1.items():
        if isinstance(v, (int, float)):
            assert f2.get(k) == pytest.approx(v, rel=1e-9, abs=1e-12), \
                f"Non-deterministic feature {k}: {v} vs {f2.get(k)}"
