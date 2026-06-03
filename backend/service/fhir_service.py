"""FHIR R4 export/import service.

Converts between i2b2 star schema models and FHIR Bundle JSON,
driven by the mapping in config/fhir_export_template.yml.
"""
import json
import logging
import os
from datetime import datetime, date
from functools import lru_cache
from typing import Any

import yaml
from sqlalchemy.orm import Session

from db.models_star import (
    PatientDimension, VisitDimension, ObservationFact, NoteFact,
)
from db.seeds.concepts import SNOMED_TO_GENDER
from service.trial_serializer import serialize_visit_detail

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load mapping
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_mapping() -> dict[str, Any]:
    path = os.path.join(os.path.dirname(__file__), "..", "config", "fhir_export_template.yml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _systems() -> dict[str, str]:
    return _load_mapping()["systems"]


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------

def _fmt_date(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.isoformat() if isinstance(val, datetime) else str(val)
    return str(val)[:10] if val else None


def _fmt_datetime(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val) if val else None


def _component(code: str, display: str, value, value_type: str, unit: str | None = None) -> dict:
    """Build a FHIR Observation.component entry."""
    sys = _systems()["metric"]
    comp: dict[str, Any] = {
        "code": {"coding": [{"system": sys, "code": code, "display": display}]},
    }
    if value_type == "valueInteger":
        comp["valueInteger"] = int(value)
    elif value_type == "valueQuantity":
        comp["valueQuantity"] = {"value": float(value), "unit": unit or ""}
    elif value_type == "valueString":
        comp["valueString"] = value if isinstance(value, str) else json.dumps(value)
    return comp


# ---------------------------------------------------------------------------
# Export: Star Schema → FHIR
# ---------------------------------------------------------------------------

def _build_patient_resource(patient: PatientDimension) -> dict:
    mapping = _load_mapping()["patient"]
    sys = _systems()
    gender_map = mapping["gender"].get("export_map", {})

    # Convert SNOMED gender code back to simple letter, then to FHIR
    simple_gender = SNOMED_TO_GENDER.get(patient.SEX_CD, patient.SEX_CD)
    gender = gender_map.get(simple_gender, mapping["gender"].get("default", "unknown"))

    resource: dict[str, Any] = {
        "resourceType": "Patient",
        "identifier": [{"system": sys["patient_id"], "value": patient.PATIENT_CD}],
        "gender": gender,
    }
    if patient.BIRTH_DATE:
        resource["birthDate"] = _fmt_date(patient.BIRTH_DATE)
    return resource


def _build_observation_from_trial(trial_dict: dict, task_type: str) -> dict:
    """Build FHIR Observation from a reconstructed trial dict."""
    sys = _systems()
    mapping = _load_mapping()["observation"]
    display_map = mapping["code"].get("display_map", {})

    resource: dict[str, Any] = {
        "resourceType": "Observation",
        "identifier": [{"system": sys["attempt_id"], "value": trial_dict.get("attempt_id", "")}],
        "status": "final",
        "code": {
            "coding": [{
                "system": sys["task_type"],
                "code": task_type,
                "display": display_map.get(task_type, task_type),
            }]
        },
    }

    if trial_dict.get("processed_at"):
        resource["effectiveDateTime"] = _fmt_datetime(trial_dict["processed_at"])
    if trial_dict.get("transcript") is not None:
        resource["valueString"] = trial_dict["transcript"]

    # Build components from metrics + fixed fields
    components: list[dict] = []

    # Fixed components from YAML spec
    for comp_spec in mapping.get("components", []):
        field = comp_spec["field"]
        # Check top-level trial dict first, then metrics
        val = trial_dict.get(field)
        if val is None:
            val = trial_dict.get("metrics", {}).get(field)
        if val is not None:
            components.append(_component(
                comp_spec["code"], comp_spec.get("display", comp_spec["code"]),
                val, comp_spec["valueType"], comp_spec.get("unit"),
            ))

    # Dynamic components from metrics
    metrics = trial_dict.get("metrics", {})
    for key, val in metrics.items():
        if val is None:
            continue
        if isinstance(val, bool):
            vt = "valueString"
        elif isinstance(val, int):
            vt = "valueInteger"
        elif isinstance(val, float):
            vt = "valueQuantity"
        else:
            vt = "valueString"
        components.append(_component(key, key, val, vt))

    if components:
        resource["component"] = components
    return resource


def _build_diagnostic_report(visit_detail: dict, observation_urls: list[str],
                              patient_url: str) -> dict:
    """Build FHIR DiagnosticReport from serialized visit detail."""
    sys = _systems()
    mapping = _load_mapping()["diagnostic_report"]

    resource: dict[str, Any] = {
        "resourceType": "DiagnosticReport",
        "identifier": [{"system": sys["session_id"],
                        "value": visit_detail.get("session_analysis_id", "")}],
        "status": "final",
        "category": [{"coding": [{
            "system": sys["category"],
            "code": mapping["category"]["code"],
            "display": mapping["category"]["display"],
        }]}],
        "code": {"coding": [{
            "system": sys["report_type"],
            "code": mapping["code"]["code"],
            "display": mapping["code"]["display"],
        }]},
        "subject": {"reference": patient_url},
        "result": [{"reference": url} for url in observation_urls],
    }

    if visit_detail.get("date"):
        resource["effectiveDateTime"] = _fmt_date(visit_detail["date"])
    if visit_detail.get("notes"):
        resource["conclusion"] = visit_detail["notes"]

    # Extensions (moca_score, group)
    extensions: list[dict] = []
    for ext_spec in mapping.get("extensions", []):
        field = ext_spec["field"]
        val = visit_detail.get(field)
        if val is not None:
            ext: dict[str, Any] = {"url": f"{sys['extension']}/{ext_spec['url_suffix']}"}
            ext[ext_spec["valueType"]] = val
            extensions.append(ext)
    if extensions:
        resource["extension"] = extensions

    return resource


def _make_bundle(entries: list[dict]) -> dict:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "entry": entries,
    }


def _entry(full_url: str, resource: dict) -> dict:
    return {"fullUrl": full_url, "resource": resource}


def _visit_to_detail(visit: VisitDimension, db: Session) -> dict:
    """Load visit observations and serialize to detail dict."""
    observations = (db.query(ObservationFact)
                    .filter(ObservationFact.ENCOUNTER_NUM == visit.ENCOUNTER_NUM)
                    .all())
    notes = (db.query(NoteFact)
             .filter(NoteFact.ENCOUNTER_NUM == visit.ENCOUNTER_NUM)
             .all())
    patient = (db.query(PatientDimension)
               .filter(PatientDimension.PATIENT_NUM == visit.PATIENT_NUM)
               .first())
    return serialize_visit_detail(visit, observations, notes, patient)


def patient_to_fhir_bundle(patient: PatientDimension, db: Session) -> dict:
    """Export a patient with all visits/observations as FHIR Bundle."""
    entries: list[dict] = []
    patient_url = f"urn:uuid:patient-{patient.PATIENT_CD}"
    entries.append(_entry(patient_url, _build_patient_resource(patient)))

    visits = (db.query(VisitDimension)
              .filter(VisitDimension.PATIENT_NUM == patient.PATIENT_NUM)
              .all())

    for visit in visits:
        detail = _visit_to_detail(visit, db)
        obs_urls: list[str] = []
        obs_entries: list[dict] = []

        for trial in detail.get("trials", []):
            attempt_id = trial.get("attempt_id", str(trial.get("id", "")))
            obs_url = f"urn:uuid:obs-{attempt_id}"
            obs_urls.append(obs_url)
            obs_entries.append(_entry(
                obs_url, _build_observation_from_trial(trial, trial["task"])
            ))

        session_id = detail.get("session_analysis_id", str(visit.ENCOUNTER_NUM))
        report_url = f"urn:uuid:report-{session_id}"
        entries.append(_entry(
            report_url, _build_diagnostic_report(detail, obs_urls, patient_url)
        ))
        entries.extend(obs_entries)

    return _make_bundle(entries)


def visit_to_fhir_bundle(visit: VisitDimension, db: Session) -> dict:
    """Export a single visit as FHIR Bundle."""
    patient = (db.query(PatientDimension)
               .filter(PatientDimension.PATIENT_NUM == visit.PATIENT_NUM)
               .first())

    patient_url = f"urn:uuid:patient-{patient.PATIENT_CD}" if patient else "urn:uuid:patient-unknown"

    entries: list[dict] = []
    if patient:
        entries.append(_entry(patient_url, _build_patient_resource(patient)))

    detail = _visit_to_detail(visit, db)

    obs_urls: list[str] = []
    obs_entries: list[dict] = []
    for trial in detail.get("trials", []):
        attempt_id = trial.get("attempt_id", str(trial.get("id", "")))
        obs_url = f"urn:uuid:obs-{attempt_id}"
        obs_urls.append(obs_url)
        obs_entries.append(_entry(
            obs_url, _build_observation_from_trial(trial, trial["task"])
        ))

    session_id = detail.get("session_analysis_id", str(visit.ENCOUNTER_NUM))
    report_url = f"urn:uuid:report-{session_id}"
    entries.append(_entry(
        report_url, _build_diagnostic_report(detail, obs_urls, patient_url)
    ))
    entries.extend(obs_entries)

    return _make_bundle(entries)


def all_to_fhir_bundle(patients: list[PatientDimension], db: Session) -> dict:
    """Export all patients as a single FHIR Bundle."""
    entries: list[dict] = []
    for patient in patients:
        patient_url = f"urn:uuid:patient-{patient.PATIENT_CD}"
        entries.append(_entry(patient_url, _build_patient_resource(patient)))

        visits = (db.query(VisitDimension)
                  .filter(VisitDimension.PATIENT_NUM == patient.PATIENT_NUM)
                  .all())

        for visit in visits:
            detail = _visit_to_detail(visit, db)
            obs_urls: list[str] = []
            obs_entries: list[dict] = []

            for trial in detail.get("trials", []):
                attempt_id = trial.get("attempt_id", str(trial.get("id", "")))
                obs_url = f"urn:uuid:obs-{attempt_id}"
                obs_urls.append(obs_url)
                obs_entries.append(_entry(
                    obs_url, _build_observation_from_trial(trial, trial["task"])
                ))

            session_id = detail.get("session_analysis_id", str(visit.ENCOUNTER_NUM))
            report_url = f"urn:uuid:report-{session_id}"
            entries.append(_entry(
                report_url, _build_diagnostic_report(detail, obs_urls, patient_url)
            ))
            entries.extend(obs_entries)

    return _make_bundle(entries)


# ---------------------------------------------------------------------------
# Import: FHIR → internal dict (unchanged contract)
# ---------------------------------------------------------------------------

def _extract_identifier(resource: dict, system: str) -> str | None:
    for ident in resource.get("identifier", []):
        if ident.get("system") == system:
            return ident.get("value")
    return None


def _extract_extension(resource: dict, url_suffix: str):
    sys = _systems()
    full_url = f"{sys['extension']}/{url_suffix}"
    for ext in resource.get("extension", []):
        if ext.get("url") == full_url:
            for key in ("valueInteger", "valueString", "valueQuantity", "valueBoolean"):
                if key in ext:
                    return ext[key]
    return None


def _reverse_gender(fhir_gender: str | None) -> str | None:
    mapping = _load_mapping()["patient"]["gender"].get("import_map", {})
    return mapping.get(fhir_gender)


def _parse_components(components: list[dict]) -> tuple[dict, dict]:
    mapping = _load_mapping()["observation"]
    fixed_codes: dict[str, tuple[str, str]] = {}
    for comp_spec in mapping.get("components", []):
        fixed_codes[comp_spec["code"]] = (comp_spec["field"], comp_spec["valueType"])

    fixed_fields: dict[str, Any] = {}
    metrics: dict[str, Any] = {}

    for comp in components:
        coding = comp.get("code", {}).get("coding", [{}])
        code = coding[0].get("code", "") if coding else ""

        val = None
        if "valueInteger" in comp:
            val = comp["valueInteger"]
        elif "valueQuantity" in comp:
            val = comp["valueQuantity"].get("value") if isinstance(comp["valueQuantity"], dict) else comp["valueQuantity"]
        elif "valueString" in comp:
            raw = comp["valueString"]
            try:
                val = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                val = raw

        if code in fixed_codes:
            field_name = fixed_codes[code][0]
            fixed_fields[field_name] = val
        else:
            metrics[code] = val

    return fixed_fields, metrics


def _observation_to_trial_data(obs: dict) -> dict:
    sys = _systems()
    code_coding = obs.get("code", {}).get("coding", [{}])
    task = code_coding[0].get("code", "") if code_coding else ""

    trial_data: dict[str, Any] = {
        "task": task,
        "attempt_id": _extract_identifier(obs, sys["attempt_id"]) or "",
        "processed_at": obs.get("effectiveDateTime"),
        "transcript": obs.get("valueString"),
    }

    fixed_fields, metrics = _parse_components(obs.get("component", []))
    trial_data.update(fixed_fields)
    if metrics:
        trial_data["metrics"] = metrics

    return trial_data


def _report_to_analysis_data(report: dict, observations_by_url: dict[str, dict]) -> dict:
    sys = _systems()

    analysis_data: dict[str, Any] = {
        "session_analysis_id": _extract_identifier(report, sys["session_id"]),
        "date": report.get("effectiveDateTime"),
        "notes": report.get("conclusion"),
        "moca_score": _extract_extension(report, "moca-score"),
        "group": _extract_extension(report, "patient-group"),
        "trials": [],
    }

    for ref in report.get("result", []):
        obs_url = ref.get("reference", "")
        obs = observations_by_url.get(obs_url)
        if obs:
            analysis_data["trials"].append(_observation_to_trial_data(obs))

    return analysis_data


def _classify_bundle(bundle: dict) -> tuple[dict | None, list[dict], dict[str, dict]]:
    patient = None
    reports: list[dict] = []
    observations: dict[str, dict] = {}

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        full_url = entry.get("fullUrl", "")
        rt = resource.get("resourceType")
        if rt == "Patient":
            patient = resource
        elif rt == "DiagnosticReport":
            reports.append(resource)
        elif rt == "Observation":
            observations[full_url] = resource

    return patient, reports, observations


def fhir_bundle_to_patient_data(bundle: dict) -> dict:
    """Convert a FHIR Bundle → dict matching POST /import/patient internal format."""
    sys = _systems()
    patient_res, reports, observations = _classify_bundle(bundle)

    if not patient_res:
        return {"patient": {"patient_id": None, "analyses": []}}

    patient_id = _extract_identifier(patient_res, sys["patient_id"])
    gender = _reverse_gender(patient_res.get("gender"))
    birth_date = patient_res.get("birthDate")

    analyses = [_report_to_analysis_data(r, observations) for r in reports]

    return {
        "patient": {
            "patient_id": patient_id,
            "gender": gender,
            "birth_date": birth_date,
            "analyses": analyses,
        }
    }


def fhir_bundle_to_analysis_data(bundle: dict) -> dict:
    """Convert a FHIR Bundle → dict matching POST /import/analysis internal format."""
    sys = _systems()
    patient_res, reports, observations = _classify_bundle(bundle)

    patient_id = _extract_identifier(patient_res, sys["patient_id"]) if patient_res else None

    if not reports:
        return {"patient_id": patient_id, "analysis": None}

    analysis_data = _report_to_analysis_data(reports[0], observations)
    return {"patient_id": patient_id, "analysis": analysis_data}
