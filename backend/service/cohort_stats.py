"""
Cohort aggregation for AcousticLab.

Reads all acoustic observations from OBSERVATION_FACT, groups them by
(gender, age_band, group), fits a Normal-Inverse-Gamma posterior per
(cell, feature), and provides scoring helpers for individual trials.

Everything is computed on demand from the current state of the DB —
no separate stats table.  For ~1500 OBSERVATION_FACT rows this stays
well under 50 ms.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import numpy as np
from sqlalchemy import or_
from sqlalchemy.orm import Session

from analysis.bayesian import (
    NIG_DEFAULT,
    NIGParams,
    posterior_nig,
    predictive_cdf,
    voice_age_score,
)
from db.models_star import (
    ObservationFact,
    PatientDimension,
    UserPatientLookup,
    VisitDimension,
)
from db.repositories.observation_repository import (
    AUDIO_DURATION_CONCEPTS,
    AUDIO_UUID_CONCEPTS,
    METRIC_CONCEPT_MAP,
)
from db.seeds.concepts import SNOMED_TO_GENDER

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────

ACOUSTIC_CATEGORY = "acoustic"
TRIAL_CATEGORIES = ("veggie", "saying", "picture", "voicesample")
SESSION_GROUP_CD = "SS:SESSION:GROUP"
COHORT_GROUPS = ("Kontrolle", "Parkinson")

# Reverse map: SS:ACOUSTIC:JITTER_LOCAL → "jitter_local"
_FEATURE_BY_CD: dict[str, str] = {
    cd: key for key, cd in METRIC_CONCEPT_MAP[ACOUSTIC_CATEGORY].items()
}
_AUDIO_UUID_CDS = tuple(AUDIO_UUID_CONCEPTS.values())
_AUDIO_DURATION_CDS = tuple(AUDIO_DURATION_CONCEPTS.values())

# 10-year age bands.  "unknown" handles missing birth_date.
AGE_BANDS = ("20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80-89", "90+")

# SHAP-top features per Shen et al. 2025 — weighted higher in the score.
SHAP_TOP_FEATURES = (
    "mfcc_3_mean",
    "mfcc_11_mean",
    "mfcc_5_mean",
    "shimmer_local",
    "jitter_local",
    "jitter_rap",
    "hnr_mean_db",
)
SCORE_WEIGHTS = {f: 1.0 for f in SHAP_TOP_FEATURES}


# ── Types ──────────────────────────────────────────────────

@dataclass(frozen=True)
class CohortCell:
    gender: str       # "m" | "f" | "d" | "unknown"
    age_band: str     # one of AGE_BANDS or "unknown"
    group: str        # "Kontrolle" | "Parkinson"


# ── Helpers ────────────────────────────────────────────────

def _gender_letter(sex_cd: Optional[str]) -> str:
    if not sex_cd:
        return "unknown"
    letter = SNOMED_TO_GENDER.get(sex_cd, sex_cd).lower()
    return letter if letter in ("m", "f", "d") else "unknown"


def _parse_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value)[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _age_band(birth_date, ref_date) -> str:
    bd = _parse_date(birth_date)
    rd = _parse_date(ref_date) or date.today()
    if bd is None:
        return "unknown"
    years = rd.year - bd.year - ((rd.month, rd.day) < (bd.month, bd.day))
    if years < 20:
        return "unknown"
    if years >= 90:
        return "90+"
    decade = (years // 10) * 10
    return f"{decade}-{decade + 9}"


# ── Cohort posterior aggregation ───────────────────────────

CohortIndex = dict[CohortCell, dict[str, NIGParams]]


def compute_cohort_posteriors(db: Session) -> CohortIndex:
    """
    Aggregate every acoustic observation into per-cell NIG posteriors.

    Returns: {CohortCell: {feature_name: NIGParams}}
    """
    # 1. group lookup per encounter
    group_rows = (
        db.query(ObservationFact.ENCOUNTER_NUM, ObservationFact.TVAL_CHAR)
        .filter(ObservationFact.CONCEPT_CD == SESSION_GROUP_CD)
        .all()
    )
    group_by_enc: dict[int, str] = {enc: tval for enc, tval in group_rows if tval}

    # 2. patient demographics + visit start_date
    pat_visit_rows = (
        db.query(
            PatientDimension.PATIENT_NUM,
            PatientDimension.SEX_CD,
            PatientDimension.BIRTH_DATE,
            VisitDimension.ENCOUNTER_NUM,
            VisitDimension.START_DATE,
        )
        .join(VisitDimension, VisitDimension.PATIENT_NUM == PatientDimension.PATIENT_NUM)
        .all()
    )
    visit_meta: dict[int, tuple[str, str, str]] = {
        row.ENCOUNTER_NUM: (row.SEX_CD, row.BIRTH_DATE, row.START_DATE)
        for row in pat_visit_rows
    }

    # 3. acoustic observations
    acoustic_rows = (
        db.query(
            ObservationFact.ENCOUNTER_NUM,
            ObservationFact.INSTANCE_NUM,
            ObservationFact.CONCEPT_CD,
            ObservationFact.NVAL_NUM,
        )
        .filter(ObservationFact.CATEGORY_CHAR == ACOUSTIC_CATEGORY)
        .filter(ObservationFact.VALTYPE_CD == "N")
        .all()
    )

    # 4. bucket values per (cell, feature)
    samples: dict[CohortCell, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for enc, _inst, cd, nval in acoustic_rows:
        if nval is None:
            continue
        feat = _FEATURE_BY_CD.get(cd)
        if feat is None:
            continue
        meta = visit_meta.get(enc)
        if meta is None:
            continue
        sex_cd, birth_date, start_date = meta
        group = group_by_enc.get(enc)
        if group not in COHORT_GROUPS:
            continue  # exclude from reference cohort
        gender = _gender_letter(sex_cd)
        age_band = _age_band(birth_date, start_date)
        cell = CohortCell(gender=gender, age_band=age_band, group=group)
        samples[cell][feat].append(float(nval))

    # 5. fit NIG posterior per (cell, feature)
    index: CohortIndex = {}
    for cell, feats in samples.items():
        index[cell] = {
            feat: posterior_nig(np.asarray(values), prior=NIG_DEFAULT)
            for feat, values in feats.items()
        }
    return index


def _merge_posteriors(*indices: dict[str, NIGParams]) -> dict[str, NIGParams]:
    """
    Merge several per-cell posterior dicts into one — used for fallback when a
    specific cell has no data (e.g. average over all age bands of one gender).

    We do this by extracting the underlying observation counts:
    NIG is closed under "extending the data", so we approximate by combining
    sufficient statistics weighted by n. Concretely we treat each posterior
    as if it had been built from `n` synthetic observations at its mean —
    a coarse but cheap fallback.
    """
    # Per-feature: unweighted average of mu/scale, summed n
    out: dict[str, list[NIGParams]] = defaultdict(list)
    for idx in indices:
        for feat, nig in idx.items():
            out[feat].append(nig)

    merged: dict[str, NIGParams] = {}
    for feat, nigs in out.items():
        if not nigs:
            continue
        total_n = sum(p.n for p in nigs)
        if total_n == 0:
            merged[feat] = nigs[0]
            continue
        weighted_mu = sum(p.mu * p.n for p in nigs) / total_n
        # combine alpha/beta additively (rough but conservative)
        kappa = sum(p.kappa for p in nigs)
        alpha = sum(p.alpha for p in nigs)
        beta = sum(p.beta for p in nigs)
        merged[feat] = NIGParams(
            mu=weighted_mu, kappa=kappa, alpha=alpha, beta=beta, n=total_n
        )
    return merged


def lookup_cell(
    index: CohortIndex,
    gender: str,
    age_band: str,
    group: str,
) -> tuple[dict[str, NIGParams], str]:
    """
    Find posteriors for the requested cell.  Falls back to broader cells
    when the exact one has no data.

    Returns (posteriors, confidence) where confidence ∈ {"high","med","low"}.
    Confidence is high if the exact cell has ≥10 samples, med if ≥5, low otherwise.
    """
    exact = index.get(CohortCell(gender, age_band, group), {})
    n_exact = next((p.n for p in exact.values()), 0)
    if n_exact >= 10:
        return exact, "high"
    if n_exact >= 5:
        return exact, "med"

    # Fallback 1: same gender + group, any age band
    same_gender = [
        p for cell, p in index.items()
        if cell.gender == gender and cell.group == group
    ]
    if same_gender:
        merged = _merge_posteriors(*same_gender)
        return merged, "low"

    # Fallback 2: same group, any gender / age band
    same_group = [p for cell, p in index.items() if cell.group == group]
    if same_group:
        return _merge_posteriors(*same_group), "low"

    return {}, "low"


# ── Trial-level scoring ────────────────────────────────────

def _trial_features(db: Session, observation_id: int) -> tuple[Optional[ObservationFact], dict[str, float]]:
    """Return the trial anchor row + dict of computed acoustic features for that trial."""
    anchor = (
        db.query(ObservationFact)
        .filter(ObservationFact.OBSERVATION_ID == observation_id)
        .first()
    )
    if anchor is None or anchor.CATEGORY_CHAR not in TRIAL_CATEGORIES:
        return None, {}

    rows = (
        db.query(ObservationFact)
        .filter(
            ObservationFact.ENCOUNTER_NUM == anchor.ENCOUNTER_NUM,
            ObservationFact.INSTANCE_NUM == anchor.INSTANCE_NUM,
            ObservationFact.CATEGORY_CHAR == ACOUSTIC_CATEGORY,
        )
        .all()
    )
    feats: dict[str, float] = {}
    for r in rows:
        key = _FEATURE_BY_CD.get(r.CONCEPT_CD)
        if key is not None and r.NVAL_NUM is not None:
            feats[key] = float(r.NVAL_NUM)
    return anchor, feats


def score_trial(db: Session, observation_id: int, index: Optional[CohortIndex] = None) -> Optional[dict]:
    """
    Compute PD_Voice_Age_Score + per-feature percentiles for a single trial.
    Returns None when the trial has no acoustic features yet.
    """
    anchor, feats = _trial_features(db, observation_id)
    if anchor is None or not feats:
        return None

    # Resolve patient + visit metadata
    patient = (
        db.query(PatientDimension)
        .filter(PatientDimension.PATIENT_NUM == anchor.PATIENT_NUM)
        .first()
    )
    visit = (
        db.query(VisitDimension)
        .filter(VisitDimension.ENCOUNTER_NUM == anchor.ENCOUNTER_NUM)
        .first()
    )
    group_obs = (
        db.query(ObservationFact)
        .filter(
            ObservationFact.ENCOUNTER_NUM == anchor.ENCOUNTER_NUM,
            ObservationFact.CONCEPT_CD == SESSION_GROUP_CD,
        )
        .first()
    )

    gender = _gender_letter(patient.SEX_CD if patient else None)
    age_band = _age_band(
        patient.BIRTH_DATE if patient else None,
        visit.START_DATE if visit else None,
    )
    group = group_obs.TVAL_CHAR if group_obs else None

    if index is None:
        index = compute_cohort_posteriors(db)

    control_post, conf_c = lookup_cell(index, gender, age_band, "Kontrolle")
    pd_post, conf_p = lookup_cell(index, gender, age_band, "Parkinson")
    confidence = min(conf_c, conf_p, key=lambda c: ["low", "med", "high"].index(c))

    score_info = voice_age_score(feats, control_post, pd_post, weights=SCORE_WEIGHTS)

    per_feature: dict[str, dict] = {}
    for feat, value in feats.items():
        c = control_post.get(feat)
        p = pd_post.get(feat)
        per_feature[feat] = {
            "value": value,
            "percentile_control": predictive_cdf(c, value) if c else None,
            "percentile_pd": predictive_cdf(p, value) if p else None,
            "n_control": c.n if c else 0,
            "n_pd": p.n if p else 0,
        }

    return {
        "trial_id": observation_id,
        "task": anchor.CATEGORY_CHAR,
        "patient_cd": patient.PATIENT_CD if patient else None,
        "gender": gender,
        "age_band": age_band,
        "group": group,
        "confidence": confidence,
        "score": score_info["score"],
        "log_likelihood_ratio": score_info["log_likelihood_ratio"],
        "n_features_used": score_info["n_features_used"],
        "per_feature": per_feature,
    }


# ── Listing all audio-bearing trials ───────────────────────

def _patient_filter(query, db: Session, user):
    """Apply patient access control unless admin."""
    if user.is_admin:
        return query
    from service.observation_builder import username_to_user_id
    return query.join(
        UserPatientLookup,
        UserPatientLookup.PATIENT_NUM == ObservationFact.PATIENT_NUM,
    ).filter(
        or_(
            UserPatientLookup.USER_ID == username_to_user_id(user.username),
            UserPatientLookup.USER_ID == 0,
        )
    )


def list_trials_with_audio(
    db: Session,
    user,
    *,
    include_score: bool = True,
) -> list[dict]:
    """
    Every trial that has an audio_uuid observation, joined with patient demo
    + group, plus a flag whether acoustic features have been computed.

    When include_score=True (default), trials with acoustic_computed=True also
    get a `score` and `confidence` inlined so the frontend can render the list
    without a per-row /score call.
    """
    audio_q = (
        db.query(
            ObservationFact.OBSERVATION_ID,
            ObservationFact.ENCOUNTER_NUM,
            ObservationFact.PATIENT_NUM,
            ObservationFact.CATEGORY_CHAR,
            ObservationFact.INSTANCE_NUM,
            ObservationFact.TVAL_CHAR,  # audio_uuid
        )
        .filter(ObservationFact.CONCEPT_CD.in_(_AUDIO_UUID_CDS))
    )
    audio_q = _patient_filter(audio_q, db, user)
    audio_rows = audio_q.all()
    if not audio_rows:
        return []

    # Index an anchor observation per trial — the audio_uuid row IS a stable
    # observation that belongs to the trial group; use IT as trial_id so
    # /trials/{id}/acoustic accepts the same id.
    trial_anchor_ids: dict[tuple[int, int, str], int] = {}
    for row in audio_rows:
        trial_anchor_ids[(row.ENCOUNTER_NUM, row.INSTANCE_NUM, row.CATEGORY_CHAR)] = row.OBSERVATION_ID

    encounters = {row.ENCOUNTER_NUM for row in audio_rows}
    patient_nums = {row.PATIENT_NUM for row in audio_rows}

    # batch-fetch patients and visits
    patients = {
        p.PATIENT_NUM: p
        for p in db.query(PatientDimension)
        .filter(PatientDimension.PATIENT_NUM.in_(patient_nums))
        .all()
    }
    visits = {
        v.ENCOUNTER_NUM: v
        for v in db.query(VisitDimension)
        .filter(VisitDimension.ENCOUNTER_NUM.in_(encounters))
        .all()
    }

    # group + duration lookup per (encounter, instance, category)
    group_rows = (
        db.query(ObservationFact.ENCOUNTER_NUM, ObservationFact.TVAL_CHAR)
        .filter(
            ObservationFact.CONCEPT_CD == SESSION_GROUP_CD,
            ObservationFact.ENCOUNTER_NUM.in_(encounters),
        )
        .all()
    )
    group_by_enc = {enc: tval for enc, tval in group_rows}

    duration_rows = (
        db.query(
            ObservationFact.ENCOUNTER_NUM,
            ObservationFact.INSTANCE_NUM,
            ObservationFact.CATEGORY_CHAR,
            ObservationFact.NVAL_NUM,
        )
        .filter(
            ObservationFact.CONCEPT_CD.in_(_AUDIO_DURATION_CDS),
            ObservationFact.ENCOUNTER_NUM.in_(encounters),
        )
        .all()
    )
    duration_by_anchor = {
        (enc, inst, cat): float(nval)
        for enc, inst, cat, nval in duration_rows
        if nval is not None
    }

    # find which (encounter, instance) pairs have acoustic rows
    acoustic_rows = (
        db.query(ObservationFact.ENCOUNTER_NUM, ObservationFact.INSTANCE_NUM)
        .filter(
            ObservationFact.CATEGORY_CHAR == ACOUSTIC_CATEGORY,
            ObservationFact.ENCOUNTER_NUM.in_(encounters),
        )
        .distinct()
        .all()
    )
    acoustic_set = {(enc, inst) for enc, inst in acoustic_rows}

    out: list[dict] = []
    for row in audio_rows:
        patient = patients.get(row.PATIENT_NUM)
        visit = visits.get(row.ENCOUNTER_NUM)
        out.append({
            "trial_id": row.OBSERVATION_ID,
            "task": row.CATEGORY_CHAR,
            "audio_uuid": row.TVAL_CHAR,
            "audio_duration_s": duration_by_anchor.get(
                (row.ENCOUNTER_NUM, row.INSTANCE_NUM, row.CATEGORY_CHAR)
            ),
            "patient_cd": patient.PATIENT_CD if patient else None,
            "gender": _gender_letter(patient.SEX_CD if patient else None),
            "age_band": _age_band(
                patient.BIRTH_DATE if patient else None,
                visit.START_DATE if visit else None,
            ),
            "birth_date": patient.BIRTH_DATE if patient else None,
            "test_date": visit.START_DATE if visit else None,
            "group": group_by_enc.get(row.ENCOUNTER_NUM),
            "encounter_num": row.ENCOUNTER_NUM,
            "patient_num": row.PATIENT_NUM,
            "acoustic_computed": (row.ENCOUNTER_NUM, row.INSTANCE_NUM) in acoustic_set,
            "score": None,
            "confidence": None,
        })

    # Inline scores for trials with acoustic features — saves N+1 requests
    # from the AcousticLab list view.
    if include_score and any(r["acoustic_computed"] for r in out):
        cohort_index = compute_cohort_posteriors(db)
        for r in out:
            if not r["acoustic_computed"]:
                continue
            try:
                s = score_trial(db, r["trial_id"], index=cohort_index)
                if s is not None:
                    r["score"] = s.get("score")
                    r["confidence"] = s.get("confidence")
            except Exception as e:
                logger.warning("Inline score failed for trial %d: %s", r["trial_id"], e)

    # newest first by encounter
    out.sort(key=lambda r: (r["encounter_num"], r["task"]), reverse=True)
    return out


def cohort_summary(index: CohortIndex) -> dict:
    """Compact JSON view of the current cohort for the /acoustic/cohort endpoint."""
    cells: list[dict] = []
    for cell, feats in sorted(
        index.items(), key=lambda kv: (kv[0].group, kv[0].gender, kv[0].age_band)
    ):
        n = next((p.n for p in feats.values()), 0)
        sample = {
            f: {"mu": feats[f].mu, "n": feats[f].n}
            for f in SHAP_TOP_FEATURES
            if f in feats
        }
        cells.append({
            "gender": cell.gender,
            "age_band": cell.age_band,
            "group": cell.group,
            "n_observations": n,
            "sample_features": sample,
        })
    return {"cells": cells, "total_cells": len(cells)}
