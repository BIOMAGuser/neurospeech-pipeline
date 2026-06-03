"""Export/Import round-trip integration tests (FHIR R4 Bundle format).

Tests verify that the star schema correctly:
- Imports FHIR Bundles → creates PATIENT_DIMENSION, VISIT_DIMENSION, OBSERVATION_FACT
- Exports star schema data → produces valid FHIR Bundles
- Roundtrips: export → re-import preserves data
- Deduplicates by session_analysis_id
"""
import uuid

import requests
from helpers import auth_headers


# ---------------------------------------------------------------------------
# Helpers: build synthetic FHIR Bundles
# ---------------------------------------------------------------------------

def _fhir_observation(task="veggie", attempt_id=None, transcript="Apfel Birne Kirsche"):
    """Build a single FHIR Observation resource for a trial."""
    aid = attempt_id or f"att-{uuid.uuid4().hex[:6]}"
    return {
        "fullUrl": f"urn:uuid:obs-{aid}",
        "resource": {
            "resourceType": "Observation",
            "identifier": [{"system": "http://speechscribe.local/fhir/attempt-id", "value": aid}],
            "status": "final",
            "code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/task-type", "code": task, "display": task}]},
            "effectiveDateTime": "2026-01-01T10:00:00+00:00",
            "valueString": transcript,
            "component": [
                {"code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/speech-metric", "code": "points", "display": "Points"}]}, "valueInteger": 3},
                {"code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/speech-metric", "code": "audio-duration", "display": "Audio Duration (seconds)"}]}, "valueQuantity": {"value": 12.5, "unit": "s"}},
                {"code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/speech-metric", "code": "total-word-count", "display": "Total Word Count"}]}, "valueInteger": 3},
                {"code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/speech-metric", "code": "correct_words", "display": "correct_words"}]}, "valueString": '["Apfel", "Birne", "Kirsche"]'},
                {"code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/speech-metric", "code": "unrelated_words", "display": "unrelated_words"}]}, "valueInteger": 0},
                {"code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/speech-metric", "code": "duplicate_count", "display": "duplicate_count"}]}, "valueInteger": 0},
            ],
        },
    }


def _make_patient_bundle(patient_id=None, session_id=None, obs_entries=None,
                          moca_score=28, group="control"):
    pid = patient_id or f"IMP-{uuid.uuid4().hex[:8]}"
    sid = session_id or f"sess-{uuid.uuid4().hex[:8]}"

    if obs_entries is None:
        obs_entries = [_fhir_observation()]

    obs_refs = [{"reference": e["fullUrl"]} for e in obs_entries]

    extensions = []
    if moca_score is not None:
        extensions.append({"url": "http://speechscribe.local/fhir/StructureDefinition/moca-score", "valueInteger": moca_score})
    if group is not None:
        extensions.append({"url": "http://speechscribe.local/fhir/StructureDefinition/patient-group", "valueString": group})

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": "2026-01-01T00:00:00Z",
        "entry": [
            {
                "fullUrl": f"urn:uuid:patient-{pid}",
                "resource": {
                    "resourceType": "Patient",
                    "identifier": [{"system": "http://speechscribe.local/fhir/patient-id", "value": pid}],
                    "gender": "male",
                    "birthDate": "1990-05-15",
                },
            },
            {
                "fullUrl": f"urn:uuid:report-{sid}",
                "resource": {
                    "resourceType": "DiagnosticReport",
                    "identifier": [{"system": "http://speechscribe.local/fhir/session-analysis-id", "value": sid}],
                    "status": "final",
                    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "SP", "display": "Speech Pathology"}]}],
                    "code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/report-type", "code": "speech-analysis", "display": "Speech Analysis Report"}]},
                    "subject": {"reference": f"urn:uuid:patient-{pid}"},
                    "effectiveDateTime": "2026-01-01",
                    "conclusion": "test import",
                    "extension": extensions,
                    "result": obs_refs,
                },
            },
            *obs_entries,
        ],
    }


def _import_and_find(base_url, token, payload):
    """Import bundle and return the patient record from /patients."""
    resp = requests.post(
        f"{base_url}/import/patient",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
    )
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    summary = resp.json()

    pid = None
    for entry in payload.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") == "Patient":
            for ident in res.get("identifier", []):
                if "patient-id" in ident.get("system", ""):
                    pid = ident["value"]
                    break

    patients = requests.get(
        f"{base_url}/patients", headers=auth_headers(token)
    ).json()
    patient = next((p for p in patients if p["patient_id"] == pid), None)
    return summary, patient


# ---------------------------------------------------------------------------
# Import Tests
# ---------------------------------------------------------------------------

class TestImportPatient:
    def test_import_new_patient(self, base_url, admin_token):
        payload = _make_patient_bundle()
        summary, patient = _import_and_find(base_url, admin_token, payload)
        assert summary["patients_created"] == 1
        assert summary["analyses_created"] == 1
        assert summary["trials_created"] == 1
        assert patient is not None
        assert patient["analysis_count"] >= 1

    def test_import_duplicate_session_skipped(self, base_url, admin_token):
        """Re-importing the same session_analysis_id should be skipped."""
        sid = f"dedup-{uuid.uuid4().hex[:8]}"
        payload = _make_patient_bundle(session_id=sid)
        _import_and_find(base_url, admin_token, payload)

        # Import again with same session_id
        resp = requests.post(
            f"{base_url}/import/patient",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json=payload,
        )
        assert resp.status_code == 200
        assert resp.json()["analyses_skipped"] == 1
        assert resp.json()["analyses_created"] == 0

    def test_import_multiple_tasks(self, base_url, admin_token):
        """Import a session with veggie + saying + picture observations."""
        obs = [
            _fhir_observation("veggie", transcript="Tomate Gurke Paprika"),
            _fhir_observation("saying", transcript="Wer im Glashaus sitzt"),
            _fhir_observation("picture", transcript="Die Frau steht am Fenster"),
        ]
        payload = _make_patient_bundle(obs_entries=obs)
        summary, patient = _import_and_find(base_url, admin_token, payload)
        assert summary["trials_created"] == 3

    def test_import_missing_patient_id_returns_422(self, base_url, admin_token):
        bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
        resp = requests.post(
            f"{base_url}/import/patient",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json=bundle,
        )
        assert resp.status_code == 422

    def test_import_missing_session_id_returns_422(self, base_url, admin_token):
        """Bundle with Patient but report missing session_analysis_id → 422."""
        pid = f"NOSID-{uuid.uuid4().hex[:6]}"
        bundle = {
            "resourceType": "Bundle", "type": "collection",
            "entry": [
                {"fullUrl": f"urn:uuid:patient-{pid}", "resource": {
                    "resourceType": "Patient",
                    "identifier": [{"system": "http://speechscribe.local/fhir/patient-id", "value": pid}],
                }},
                {"fullUrl": "urn:uuid:report-x", "resource": {
                    "resourceType": "DiagnosticReport",
                    "identifier": [],  # No session_analysis_id
                    "status": "final",
                    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "SP"}]}],
                    "code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/report-type", "code": "speech-analysis"}]},
                    "subject": {"reference": f"urn:uuid:patient-{pid}"},
                    "result": [],
                }},
            ],
        }
        resp = requests.post(
            f"{base_url}/import/patient",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json=bundle,
        )
        assert resp.status_code == 422


class TestImportAnalysis:
    def test_import_analysis_creates_patient_if_needed(self, base_url, admin_token):
        pid = f"ANAIMP-{uuid.uuid4().hex[:6]}"
        bundle = _make_patient_bundle(patient_id=pid)
        resp = requests.post(
            f"{base_url}/import/analysis",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json=bundle,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["patients_created"] == 1 or data["analyses_created"] == 1


# ---------------------------------------------------------------------------
# Export Tests
# ---------------------------------------------------------------------------

class TestExportPatient:
    def test_export_patient_produces_fhir_bundle(self, base_url, admin_token):
        """Import a patient, then export → valid FHIR Bundle."""
        payload = _make_patient_bundle()
        _, patient = _import_and_find(base_url, admin_token, payload)
        assert patient is not None

        resp = requests.get(
            f"{base_url}/patients/{patient['id']}/export",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"
        assert len(bundle["entry"]) >= 3  # Patient + DiagnosticReport + Observation(s)

        # Verify resource types present
        types = {e["resource"]["resourceType"] for e in bundle["entry"]}
        assert "Patient" in types
        assert "DiagnosticReport" in types
        assert "Observation" in types

    def test_export_preserves_patient_data(self, base_url, admin_token):
        """Exported Patient resource should match imported data."""
        pid = f"EXPTEST-{uuid.uuid4().hex[:6]}"
        payload = _make_patient_bundle(patient_id=pid, moca_score=25, group="Parkinson")
        _, patient = _import_and_find(base_url, admin_token, payload)
        assert patient is not None

        resp = requests.get(
            f"{base_url}/patients/{patient['id']}/export",
            headers=auth_headers(admin_token),
        )
        bundle = resp.json()

        # Find Patient resource
        patient_res = next(
            e["resource"] for e in bundle["entry"]
            if e["resource"]["resourceType"] == "Patient"
        )
        assert patient_res["gender"] == "male"
        assert patient_res["birthDate"] == "1990-05-15"

        # Find DiagnosticReport
        report = next(
            e["resource"] for e in bundle["entry"]
            if e["resource"]["resourceType"] == "DiagnosticReport"
        )
        assert report.get("conclusion") == "test import"

    def test_export_analysis(self, base_url, admin_token):
        """Export a single analysis (visit) as FHIR Bundle."""
        payload = _make_patient_bundle()
        _, patient = _import_and_find(base_url, admin_token, payload)
        assert patient is not None

        analyses = requests.get(
            f"{base_url}/patients/{patient['id']}/analyses",
            headers=auth_headers(admin_token),
        ).json()
        assert len(analyses) >= 1

        resp = requests.get(
            f"{base_url}/analyses/{analyses[0]['id']}/export",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle["resourceType"] == "Bundle"


class TestExportAll:
    def test_bulk_export(self, base_url, admin_token):
        resp = requests.get(f"{base_url}/export", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        bundle = resp.json()
        assert bundle["resourceType"] == "Bundle"
        assert "entry" in bundle

    def test_bulk_export_requires_auth(self, base_url):
        resp = requests.get(f"{base_url}/export")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Roundtrip Tests
# ---------------------------------------------------------------------------

class TestRoundtrip:
    def test_import_export_reimport(self, base_url, admin_token):
        """Import → Export → Re-import should work without data loss."""
        pid = f"ROUND-{uuid.uuid4().hex[:6]}"
        original = _make_patient_bundle(patient_id=pid)

        # 1. Import
        resp = requests.post(
            f"{base_url}/import/patient",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json=original,
        )
        assert resp.status_code == 200

        # 2. Find patient
        patients = requests.get(
            f"{base_url}/patients", headers=auth_headers(admin_token)
        ).json()
        patient = next(p for p in patients if p["patient_id"] == pid)

        # 3. Export
        export_resp = requests.get(
            f"{base_url}/patients/{patient['id']}/export",
            headers=auth_headers(admin_token),
        )
        assert export_resp.status_code == 200
        exported_bundle = export_resp.json()

        # 4. Re-import (should be skipped due to duplicate session_analysis_id)
        reimport_resp = requests.post(
            f"{base_url}/import/patient",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json=exported_bundle,
        )
        assert reimport_resp.status_code == 200
        assert reimport_resp.json()["analyses_skipped"] >= 1


# ---------------------------------------------------------------------------
# Delete Tests
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_analysis_cascades(self, base_url, admin_token):
        """Deleting a visit should remove all observations."""
        payload = _make_patient_bundle()
        _, patient = _import_and_find(base_url, admin_token, payload)
        assert patient is not None

        analyses = requests.get(
            f"{base_url}/patients/{patient['id']}/analyses",
            headers=auth_headers(admin_token),
        ).json()
        assert len(analyses) >= 1

        analysis_id = analyses[0]["id"]
        resp = requests.delete(
            f"{base_url}/analyses/{analysis_id}",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200

        # Verify analysis is gone
        detail_resp = requests.get(
            f"{base_url}/analyses/{analysis_id}",
            headers=auth_headers(admin_token),
        )
        assert detail_resp.status_code == 404

    def test_delete_patient_cascades(self, base_url, admin_token):
        """Deleting a patient should remove all visits and observations."""
        pid = f"DELCAS-{uuid.uuid4().hex[:6]}"
        payload = _make_patient_bundle(patient_id=pid)
        _, patient = _import_and_find(base_url, admin_token, payload)
        assert patient is not None

        resp = requests.delete(
            f"{base_url}/patients/{patient['id']}",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200

        # Verify patient is gone
        patients_after = requests.get(
            f"{base_url}/patients", headers=auth_headers(admin_token)
        ).json()
        assert not any(p["patient_id"] == pid for p in patients_after)

    def test_delete_nonexistent_analysis_returns_404(self, base_url, admin_token):
        resp = requests.delete(
            f"{base_url}/analyses/999999",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 404

    def test_delete_nonexistent_patient_returns_404(self, base_url, admin_token):
        resp = requests.delete(
            f"{base_url}/patients/999999",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Analysis Detail Tests (star schema specific)
# ---------------------------------------------------------------------------

class TestAnalysisDetail:
    def test_analysis_detail_returns_trials(self, base_url, admin_token):
        """GET /analyses/{id} should return reconstructed trials from observations."""
        payload = _make_patient_bundle()
        _, patient = _import_and_find(base_url, admin_token, payload)
        assert patient is not None

        analyses = requests.get(
            f"{base_url}/patients/{patient['id']}/analyses",
            headers=auth_headers(admin_token),
        ).json()

        detail = requests.get(
            f"{base_url}/analyses/{analyses[0]['id']}",
            headers=auth_headers(admin_token),
        ).json()

        assert "trials" in detail
        assert len(detail["trials"]) >= 1
        trial = detail["trials"][0]
        assert "task" in trial
        assert "metrics" in trial
        assert "transcript" in trial

    def test_analysis_detail_has_session_fields(self, base_url, admin_token):
        """Session-level fields (moca_score, group, notes) should be returned."""
        pid = f"SESSF-{uuid.uuid4().hex[:6]}"
        payload = _make_patient_bundle(patient_id=pid, moca_score=22, group="Parkinson")
        _, patient = _import_and_find(base_url, admin_token, payload)
        assert patient is not None

        analyses = requests.get(
            f"{base_url}/patients/{patient['id']}/analyses",
            headers=auth_headers(admin_token),
        ).json()

        detail = requests.get(
            f"{base_url}/analyses/{analyses[0]['id']}",
            headers=auth_headers(admin_token),
        ).json()

        assert detail.get("notes") == "test import"
        assert detail.get("patient_id") == pid

    def test_patient_list_has_analysis_count(self, base_url, admin_token):
        """Patient listing should include analysis_count from VISIT_DIMENSION."""
        pid = f"CNT-{uuid.uuid4().hex[:6]}"
        payload = _make_patient_bundle(patient_id=pid)
        _, patient = _import_and_find(base_url, admin_token, payload)
        assert patient is not None
        assert patient["analysis_count"] >= 1

    def test_patient_analyses_list_has_trial_count(self, base_url, admin_token):
        """Analysis listing should include trial_count from OBSERVATION_FACT categories."""
        pid = f"TCNT-{uuid.uuid4().hex[:6]}"
        obs = [_fhir_observation("veggie"), _fhir_observation("picture")]
        payload = _make_patient_bundle(patient_id=pid, obs_entries=obs)
        _, patient = _import_and_find(base_url, admin_token, payload)
        assert patient is not None

        analyses = requests.get(
            f"{base_url}/patients/{patient['id']}/analyses",
            headers=auth_headers(admin_token),
        ).json()
        assert len(analyses) >= 1
        assert analyses[0]["trial_count"] >= 2
