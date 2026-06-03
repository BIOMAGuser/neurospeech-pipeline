"""
AcousticLab integration tests.

Cover both the pure Bayesian math (no DB) and the new endpoints:
  GET  /acoustic/trials
  GET  /trials/{id}/acoustic/score
  GET  /acoustic/cohort

Smoke tests for /score depend on at least one trial having acoustic
features already computed (test_05 → test_10 chain).
"""
from pathlib import Path

import numpy as np
import pytest
import requests
from helpers import auth_headers

FIXTURES = Path(__file__).parent / "fixtures"


# ── Pure Bayesian math (no DB / no HTTP) ───────────────────

class TestBayesianMath:

    def test_posterior_collapses_to_data_for_many_observations(self):
        from analysis.bayesian import posterior_nig, NIG_DEFAULT
        rng = np.random.default_rng(42)
        true_mu, true_sigma = 5.0, 0.5
        samples = rng.normal(true_mu, true_sigma, size=2000)
        post = posterior_nig(samples, prior=NIG_DEFAULT)
        # μ_n should be near the sample mean
        assert abs(post.mu - samples.mean()) < 0.05
        # 2α/2 = α ≈ n/2 + 1
        assert post.alpha == pytest.approx(2000 / 2 + 1)
        assert post.n == 2000

    def test_predictive_cdf_at_mean_is_half(self):
        from analysis.bayesian import posterior_nig, predictive_cdf
        post = posterior_nig(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        # symmetric Student-t centered on μ_n
        assert predictive_cdf(post, post.mu) == pytest.approx(0.5, abs=1e-9)

    def test_score_separates_two_well_separated_distributions(self):
        from analysis.bayesian import posterior_nig, voice_age_score
        rng = np.random.default_rng(0)
        control = posterior_nig(rng.normal(0.0, 1.0, size=200))
        pd = posterior_nig(rng.normal(5.0, 1.0, size=200))
        # Sample clearly from the PD distribution
        result = voice_age_score(
            target_features={"x": 5.0},
            control_nig={"x": control},
            pd_nig={"x": pd},
        )
        assert result["score"] is not None
        assert result["score"] > 0.95
        # And clearly from control
        result2 = voice_age_score(
            target_features={"x": 0.0},
            control_nig={"x": control},
            pd_nig={"x": pd},
        )
        assert result2["score"] < 0.05

    def test_score_returns_none_when_no_overlap_features(self):
        from analysis.bayesian import voice_age_score, NIG_DEFAULT
        out = voice_age_score(
            target_features={"a": 1.0},
            control_nig={"b": NIG_DEFAULT},
            pd_nig={"b": NIG_DEFAULT},
        )
        assert out["score"] is None
        assert out["n_features_used"] == 0

    def test_age_band_buckets(self):
        from service.cohort_stats import _age_band
        assert _age_band("1960-01-01", "2025-01-01") == "60-69"
        assert _age_band("1990-06-15", "2026-05-10") == "30-39"
        assert _age_band("1925-01-01", "2026-01-01") == "90+"
        assert _age_band(None, "2026-01-01") == "unknown"
        assert _age_band("invalid", "2026-01-01") == "unknown"

    def test_gender_letter_mapping(self):
        from service.cohort_stats import _gender_letter
        assert _gender_letter("SCTID: 407374003") == "f"
        assert _gender_letter("SCTID: 407375002") == "m"
        assert _gender_letter("SCTID: 394744001") == "d"
        assert _gender_letter(None) == "unknown"
        assert _gender_letter("") == "unknown"


# ── Endpoint tests ─────────────────────────────────────────

class TestEndpoints:

    def test_list_trials_unauthorized(self, base_url):
        resp = requests.get(f"{base_url}/acoustic/trials")
        assert resp.status_code == 401

    def test_cohort_unauthorized(self, base_url):
        resp = requests.get(f"{base_url}/acoustic/cohort")
        assert resp.status_code == 401

    def test_list_trials_returns_array(self, base_url, admin_token):
        resp = requests.get(
            f"{base_url}/acoustic/trials", headers=auth_headers(admin_token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if not data:
            pytest.skip("No trials with audio in DB")
        # Schema check on first item
        item = data[0]
        for key in ("trial_id", "task", "audio_uuid", "patient_cd",
                    "gender", "age_band", "group", "acoustic_computed"):
            assert key in item

    def test_cohort_summary_shape(self, base_url, admin_token):
        resp = requests.get(
            f"{base_url}/acoustic/cohort", headers=auth_headers(admin_token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "cells" in data
        assert "total_cells" in data
        assert isinstance(data["cells"], list)

    def test_score_404_when_no_acoustic_features(self, base_url, admin_token):
        # Find a trial that does NOT have acoustic features
        list_resp = requests.get(
            f"{base_url}/acoustic/trials", headers=auth_headers(admin_token)
        )
        if list_resp.status_code != 200 or not list_resp.json():
            pytest.skip("No trials available")
        no_feat = next(
            (t for t in list_resp.json() if not t["acoustic_computed"]),
            None,
        )
        if not no_feat:
            pytest.skip("All trials already have acoustic features")
        resp = requests.get(
            f"{base_url}/trials/{no_feat['trial_id']}/acoustic/score",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 404

    def test_score_smoke(self, base_url, admin_token):
        list_resp = requests.get(
            f"{base_url}/acoustic/trials", headers=auth_headers(admin_token)
        )
        if list_resp.status_code != 200 or not list_resp.json():
            pytest.skip("No trials available")
        with_feat = next(
            (t for t in list_resp.json() if t["acoustic_computed"]),
            None,
        )
        if not with_feat:
            pytest.skip("No trial with acoustic features yet")

        resp = requests.get(
            f"{base_url}/trials/{with_feat['trial_id']}/acoustic/score",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        for key in ("trial_id", "gender", "age_band", "group",
                    "confidence", "score", "per_feature", "n_features_used"):
            assert key in data
        assert data["confidence"] in ("low", "med", "high")
        # per_feature must contain the SHAP-top features when feats are present
        for feat in ("jitter_local", "shimmer_local", "hnr_mean_db", "mfcc_3_mean"):
            assert feat in data["per_feature"]
            entry = data["per_feature"][feat]
            assert "value" in entry
            # percentiles may be None when cohort empty for that cell
            assert "percentile_control" in entry
            assert "percentile_pd" in entry
