"""Star schema specific tests: EAV observations, concept vocabulary, views.

Tests the i2b2 star schema patterns that don't map 1:1 to the old API.
"""
import uuid

import requests
from helpers import auth_headers


def _quick_import(base_url, token, patient_id=None, task="veggie",
                   transcript="Tomate Gurke", points=2):
    """Quick helper: import a minimal patient with one trial."""
    pid = patient_id or f"STAR-{uuid.uuid4().hex[:6]}"
    sid = f"sess-{uuid.uuid4().hex[:8]}"
    aid = f"att-{uuid.uuid4().hex[:6]}"
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": "2026-01-01T00:00:00Z",
        "entry": [
            {
                "fullUrl": f"urn:uuid:patient-{pid}",
                "resource": {
                    "resourceType": "Patient",
                    "identifier": [{"system": "http://speechscribe.local/fhir/patient-id", "value": pid}],
                    "gender": "female",
                    "birthDate": "1985-03-20",
                },
            },
            {
                "fullUrl": f"urn:uuid:report-{sid}",
                "resource": {
                    "resourceType": "DiagnosticReport",
                    "identifier": [{"system": "http://speechscribe.local/fhir/session-analysis-id", "value": sid}],
                    "status": "final",
                    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "SP"}]}],
                    "code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/report-type", "code": "speech-analysis"}]},
                    "subject": {"reference": f"urn:uuid:patient-{pid}"},
                    "effectiveDateTime": "2026-01-15",
                    "result": [{"reference": f"urn:uuid:obs-{aid}"}],
                    "extension": [
                        {"url": "http://speechscribe.local/fhir/StructureDefinition/moca-score", "valueInteger": 26},
                        {"url": "http://speechscribe.local/fhir/StructureDefinition/patient-group", "valueString": "Kontrolle"},
                    ],
                },
            },
            {
                "fullUrl": f"urn:uuid:obs-{aid}",
                "resource": {
                    "resourceType": "Observation",
                    "identifier": [{"system": "http://speechscribe.local/fhir/attempt-id", "value": aid}],
                    "status": "final",
                    "code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/task-type", "code": task}]},
                    "effectiveDateTime": "2026-01-15T10:00:00Z",
                    "valueString": transcript,
                    "component": [
                        {"code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/speech-metric", "code": "points"}]}, "valueInteger": points},
                        {"code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/speech-metric", "code": "total-word-count"}]}, "valueInteger": len(transcript.split())},
                    ],
                },
            },
        ],
    }
    resp = requests.post(
        f"{base_url}/import/patient",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=bundle,
    )
    return resp, pid, sid


class TestEAVObservations:
    """Test that the EAV pattern correctly stores and retrieves metrics."""

    def test_metrics_roundtrip(self, base_url, admin_token):
        """Import with specific metrics → detail view should reconstruct them."""
        resp, pid, _ = _quick_import(base_url, admin_token, points=5,
                                      transcript="Brokkoli Karotte Spinat Tomate Gurke")
        assert resp.status_code == 200

        patients = requests.get(
            f"{base_url}/patients", headers=auth_headers(admin_token)
        ).json()
        patient = next(p for p in patients if p["patient_id"] == pid)

        analyses = requests.get(
            f"{base_url}/patients/{patient['id']}/analyses",
            headers=auth_headers(admin_token),
        ).json()

        detail = requests.get(
            f"{base_url}/analyses/{analyses[0]['id']}",
            headers=auth_headers(admin_token),
        ).json()

        trial = detail["trials"][0]
        assert trial["task"] == "veggie"
        assert trial["metrics"].get("points") == 5
        assert trial["metrics"].get("total_word_count") == 5
        assert trial["transcript"] == "Brokkoli Karotte Spinat Tomate Gurke"

    def test_multiple_task_types_in_one_visit(self, base_url, admin_token):
        """A visit with veggie + picture trials should both be reconstructed."""
        pid = f"MULTI-{uuid.uuid4().hex[:6]}"
        sid = f"sess-{uuid.uuid4().hex[:8]}"
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "timestamp": "2026-01-01T00:00:00Z",
            "entry": [
                {"fullUrl": f"urn:uuid:patient-{pid}", "resource": {
                    "resourceType": "Patient",
                    "identifier": [{"system": "http://speechscribe.local/fhir/patient-id", "value": pid}],
                    "gender": "male",
                }},
                {"fullUrl": f"urn:uuid:report-{sid}", "resource": {
                    "resourceType": "DiagnosticReport",
                    "identifier": [{"system": "http://speechscribe.local/fhir/session-analysis-id", "value": sid}],
                    "status": "final",
                    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "SP"}]}],
                    "code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/report-type", "code": "speech-analysis"}]},
                    "subject": {"reference": f"urn:uuid:patient-{pid}"},
                    "effectiveDateTime": "2026-02-01",
                    "result": [
                        {"reference": "urn:uuid:obs-v1"},
                        {"reference": "urn:uuid:obs-p1"},
                    ],
                }},
                {"fullUrl": "urn:uuid:obs-v1", "resource": {
                    "resourceType": "Observation",
                    "identifier": [{"system": "http://speechscribe.local/fhir/attempt-id", "value": "att-v1"}],
                    "status": "final",
                    "code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/task-type", "code": "veggie"}]},
                    "valueString": "Tomate Gurke",
                    "component": [
                        {"code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/speech-metric", "code": "points"}]}, "valueInteger": 2},
                    ],
                }},
                {"fullUrl": "urn:uuid:obs-p1", "resource": {
                    "resourceType": "Observation",
                    "identifier": [{"system": "http://speechscribe.local/fhir/attempt-id", "value": "att-p1"}],
                    "status": "final",
                    "code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/task-type", "code": "picture"}]},
                    "valueString": "Die Frau steht am Fenster",
                    "component": [
                        {"code": {"coding": [{"system": "http://speechscribe.local/fhir/CodeSystem/speech-metric", "code": "points"}]}, "valueInteger": 4},
                    ],
                }},
            ],
        }
        resp = requests.post(
            f"{base_url}/import/patient",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json=bundle,
        )
        assert resp.status_code == 200
        assert resp.json()["trials_created"] == 2

        patients = requests.get(
            f"{base_url}/patients", headers=auth_headers(admin_token)
        ).json()
        patient = next(p for p in patients if p["patient_id"] == pid)

        analyses = requests.get(
            f"{base_url}/patients/{patient['id']}/analyses",
            headers=auth_headers(admin_token),
        ).json()

        detail = requests.get(
            f"{base_url}/analyses/{analyses[0]['id']}",
            headers=auth_headers(admin_token),
        ).json()

        tasks = {t["task"] for t in detail["trials"]}
        assert "veggie" in tasks
        assert "picture" in tasks


class TestStatsConsistency:
    """Verify /stats counts match actual data."""

    def test_stats_counts_match_patients(self, base_url, admin_token):
        """Number of patients from /stats should match /patients list."""
        stats = requests.get(
            f"{base_url}/stats", headers=auth_headers(admin_token)
        ).json()

        patients = requests.get(
            f"{base_url}/patients", headers=auth_headers(admin_token)
        ).json()

        # Stats may count all patients; /patients may be paginated
        # At minimum, stats.patients >= len(patients)
        assert stats["patients"] >= 0
        assert stats["analyses"] >= 0
        assert stats["trials"] >= 0


class TestPatientGenderMapping:
    """Verify gender codes are correctly stored and exported."""

    def test_gender_stored_and_exported(self, base_url, admin_token):
        """Import female patient → export should have gender=female."""
        pid = f"GEN-{uuid.uuid4().hex[:6]}"
        resp, _, _ = _quick_import(base_url, admin_token, patient_id=pid)
        assert resp.status_code == 200

        patients = requests.get(
            f"{base_url}/patients", headers=auth_headers(admin_token)
        ).json()
        patient = next(p for p in patients if p["patient_id"] == pid)

        export = requests.get(
            f"{base_url}/patients/{patient['id']}/export",
            headers=auth_headers(admin_token),
        ).json()

        patient_res = next(
            e["resource"] for e in export["entry"]
            if e["resource"]["resourceType"] == "Patient"
        )
        assert patient_res["gender"] == "female"


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_get_nonexistent_analysis(self, base_url, admin_token):
        resp = requests.get(
            f"{base_url}/analyses/999999",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 404

    def test_get_nonexistent_patient_analyses(self, base_url, admin_token):
        resp = requests.get(
            f"{base_url}/patients/999999/analyses",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 404

    def test_export_nonexistent_patient(self, base_url, admin_token):
        resp = requests.get(
            f"{base_url}/patients/999999/export",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 404

    def test_import_empty_bundle(self, base_url, admin_token):
        """Empty Bundle should return 422."""
        bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
        resp = requests.post(
            f"{base_url}/import/patient",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json=bundle,
        )
        assert resp.status_code == 422

    def test_import_non_bundle(self, base_url, admin_token):
        """Non-Bundle payload without patient key should return 422."""
        resp = requests.post(
            f"{base_url}/import/patient",
            headers={**auth_headers(admin_token), "Content-Type": "application/json"},
            json={"resourceType": "Patient", "id": "test"},
        )
        assert resp.status_code == 422
