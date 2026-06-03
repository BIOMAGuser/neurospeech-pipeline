"""
Seed data for CONCEPT_DIMENSION and CODE_LOOKUP tables.

Defines the SpeechScribe measurement vocabulary following the BEST DB Manager pattern.
All concept codes use the SS: (SpeechScribe) namespace prefix.
"""

from datetime import datetime

_NOW = datetime.now().isoformat()
_SOURCE = "SPEECHSCRIBE_SEED"


def get_concept_seeds() -> list[dict]:
    """Return CONCEPT_DIMENSION seed rows for SpeechScribe tasks and metrics."""
    concepts = []

    def _c(code: str, name: str, category: str, valtype: str = "N",
           unit: str = None, path: str = None):
        concepts.append({
            "CONCEPT_CD": code,
            "NAME_CHAR": name,
            "CATEGORY_CHAR": category,
            "VALTYPE_CD": valtype,
            "UNIT_CD": unit,
            "CONCEPT_PATH": path or f"\\SpeechScribe\\{category}\\{code.split(':')[-1].lower()}\\",
            "SOURCESYSTEM_CD": _SOURCE,
            "IMPORT_DATE": _NOW,
            "UPDATE_DATE": _NOW,
        })

    # ── Veggie Task (Semantic Fluency) ────────────────────────
    _c("SS:VEGGIE:POINTS", "Semantische Fluenz: korrekte Gemüse", "veggie", "N", "count")
    _c("SS:VEGGIE:CORRECT_WORDS", "Liste korrekter Gemüse", "veggie", "T")
    _c("SS:VEGGIE:UNRELATED_WORDS", "Anzahl nicht-verwandter Wörter", "veggie", "N", "count")
    _c("SS:VEGGIE:UNRELATED_WORDS_LIST", "Liste nicht-verwandter Wörter", "veggie", "T")
    _c("SS:VEGGIE:DUPLICATE_COUNT", "Anzahl Duplikate", "veggie", "N", "count")
    _c("SS:VEGGIE:TOTAL_WORD_COUNT", "Gesamtwortanzahl", "veggie", "N", "count")
    _c("SS:VEGGIE:FILLER_WORD_COUNT", "Anzahl Füllwörter", "veggie", "N", "count")
    _c("SS:VEGGIE:TRANSCRIPT", "Transkription", "veggie", "T")
    _c("SS:VEGGIE:AUDIO_UUID", "Audio-Datei UUID", "veggie", "T")
    _c("SS:VEGGIE:AUDIO_DURATION", "Aufnahmedauer", "veggie", "N", "s")

    # ── Saying Task (Proverb Understanding) ───────────────────
    _c("SS:SAYING:POINTS", "Sprichwort-Verständnis Score", "saying", "N", "count")
    _c("SS:SAYING:FILLER_WORD_COUNT", "Anzahl Füllwörter", "saying", "N", "count")
    _c("SS:SAYING:TOTAL_WORD_COUNT", "Gesamtwortanzahl", "saying", "N", "count")
    _c("SS:SAYING:TRANSCRIPT", "Transkription", "saying", "T")
    _c("SS:SAYING:AUDIO_UUID", "Audio-Datei UUID", "saying", "T")
    _c("SS:SAYING:AUDIO_DURATION", "Aufnahmedauer", "saying", "N", "s")

    # ── Picture Task (Cookie Theft Description) ───────────────
    _c("SS:PICTURE:POINTS", "Bildbeschreibung Konzept-Score", "picture", "N", "count")
    _c("SS:PICTURE:SENTENCE_COUNT", "Anzahl Sätze", "picture", "N", "count")
    _c("SS:PICTURE:VERB_COUNT", "Anzahl Verben", "picture", "N", "count")
    _c("SS:PICTURE:NOUN_COUNT", "Anzahl Nomen", "picture", "N", "count")
    _c("SS:PICTURE:PRONOUN_COUNT", "Anzahl Pronomen", "picture", "N", "count")
    _c("SS:PICTURE:ADVERB_COUNT", "Anzahl Adverbien", "picture", "N", "count")
    _c("SS:PICTURE:ADJECTIVE_COUNT", "Anzahl Adjektive", "picture", "N", "count")
    _c("SS:PICTURE:VERB_RATIO", "Verb-Anteil", "picture", "N", "ratio")
    _c("SS:PICTURE:NOUN_RATIO", "Nomen-Anteil", "picture", "N", "ratio")
    _c("SS:PICTURE:PRONOUN_RATIO", "Pronomen-Anteil", "picture", "N", "ratio")
    _c("SS:PICTURE:ADVERB_RATIO", "Adverb-Anteil", "picture", "N", "ratio")
    _c("SS:PICTURE:ADJECTIVE_RATIO", "Adjektiv-Anteil", "picture", "N", "ratio")
    _c("SS:PICTURE:TTR", "Type-Token-Ratio", "picture", "N", "ratio")
    _c("SS:PICTURE:AVG_SENTENCE_LENGTH", "Durchschnittliche Satzlänge", "picture", "N", "words")
    _c("SS:PICTURE:FILLER_WORD_COUNT", "Anzahl Füllwörter", "picture", "N", "count")
    _c("SS:PICTURE:TOTAL_WORD_COUNT", "Gesamtwortanzahl", "picture", "N", "count")
    _c("SS:PICTURE:TRANSCRIPT", "Transkription", "picture", "T")
    _c("SS:PICTURE:AUDIO_UUID", "Audio-Datei UUID", "picture", "T")
    _c("SS:PICTURE:AUDIO_DURATION", "Aufnahmedauer", "picture", "N", "s")

    # ── Voice Sample (sustained vowels, read text, free speech) ──
    # Used for acoustic-only recordings (e.g. MDVR-KCL demo data).
    # No GPT/NLP/scoring — just the audio anchor for /trials/{id}/acoustic.
    _c("SS:VOICESAMPLE:TRANSCRIPT", "Transkription", "voicesample", "T")
    _c("SS:VOICESAMPLE:AUDIO_UUID", "Audio-Datei UUID", "voicesample", "T")
    _c("SS:VOICESAMPLE:AUDIO_DURATION", "Aufnahmedauer", "voicesample", "N", "s")

    # ── Session-Level Observations ────────────────────────────
    _c("SS:SESSION:MOCA_SCORE", "MoCA Total Score", "session", "N", "count",
       "\\SpeechScribe\\session\\moca_score\\")
    _c("SS:SESSION:GROUP", "Patientengruppe", "session", "T", None,
       "\\SpeechScribe\\session\\group\\")
    _c("SS:SESSION:SESSION_ID", "Session-Analyse-ID", "session", "T", None,
       "\\SpeechScribe\\session\\session_id\\")

    # ── Acoustic Features (task-agnostic, per audio recording) ────
    # F0 / Pitch
    _c("SS:ACOUSTIC:F0_MEAN_HZ", "F0 mean", "acoustic", "N", "Hz")
    _c("SS:ACOUSTIC:F0_STD_HZ", "F0 standard deviation", "acoustic", "N", "Hz")
    _c("SS:ACOUSTIC:F0_MIN_HZ", "F0 minimum", "acoustic", "N", "Hz")
    _c("SS:ACOUSTIC:F0_MAX_HZ", "F0 maximum", "acoustic", "N", "Hz")
    # Jitter (frequency perturbation)
    _c("SS:ACOUSTIC:JITTER_LOCAL", "Jitter (local)", "acoustic", "N", "ratio")
    _c("SS:ACOUSTIC:JITTER_RAP", "Jitter (rap)", "acoustic", "N", "ratio")
    _c("SS:ACOUSTIC:JITTER_PPQ5", "Jitter (ppq5)", "acoustic", "N", "ratio")
    # Shimmer (amplitude perturbation)
    _c("SS:ACOUSTIC:SHIMMER_LOCAL", "Shimmer (local)", "acoustic", "N", "ratio")
    _c("SS:ACOUSTIC:SHIMMER_APQ3", "Shimmer (apq3)", "acoustic", "N", "ratio")
    _c("SS:ACOUSTIC:SHIMMER_APQ5", "Shimmer (apq5)", "acoustic", "N", "ratio")
    _c("SS:ACOUSTIC:SHIMMER_APQ11", "Shimmer (apq11)", "acoustic", "N", "ratio")
    # HNR
    _c("SS:ACOUSTIC:HNR_MEAN_DB", "Harmonics-to-Noise Ratio mean", "acoustic", "N", "dB")
    _c("SS:ACOUSTIC:HNR_STD_DB", "Harmonics-to-Noise Ratio std", "acoustic", "N", "dB")
    # MFCC-13 (mean + std)
    for i in range(1, 14):
        _c(f"SS:ACOUSTIC:MFCC_{i}_MEAN", f"MFCC coefficient {i} mean", "acoustic", "N")
        _c(f"SS:ACOUSTIC:MFCC_{i}_STD", f"MFCC coefficient {i} std", "acoustic", "N")

    return concepts


def get_code_lookup_seeds() -> list[dict]:
    """Return CODE_LOOKUP seed rows for reference data."""
    codes = []

    def _code(code: str, table: str, column: str, name: str):
        codes.append({
            "CODE_CD": code,
            "TABLE_CD": table,
            "COLUMN_CD": column,
            "NAME_CHAR": name,
            "SOURCESYSTEM_CD": _SOURCE,
            "IMPORT_DATE": _NOW,
            "UPDATE_DATE": _NOW,
        })

    # Gender codes (SNOMED-CT)
    _code("SCTID: 407374003", "PATIENT_DIMENSION", "SEX_CD", "Weiblich")
    _code("SCTID: 407375002", "PATIENT_DIMENSION", "SEX_CD", "Männlich")
    _code("SCTID: 394744001", "PATIENT_DIMENSION", "SEX_CD", "Divers")

    # Vital status codes
    _code("SCTID: 438949009", "PATIENT_DIMENSION", "VITAL_STATUS_CD", "Lebendig")
    _code("SCTID: 419099009", "PATIENT_DIMENSION", "VITAL_STATUS_CD", "Verstorben")

    # Visit status codes
    _code("SCTID: 55561003", "VISIT_DIMENSION", "ACTIVE_STATUS_CD", "Aktiv")

    # Visit type codes
    _code("O", "VISIT_DIMENSION", "INOUT_CD", "Ambulant")
    _code("I", "VISIT_DIMENSION", "INOUT_CD", "Stationär")
    _code("E", "VISIT_DIMENSION", "INOUT_CD", "Notfall")

    # Task type codes (for CATEGORY_CHAR)
    _code("veggie", "OBSERVATION_FACT", "CATEGORY_CHAR", "Semantische Fluenz (Gemüse)")
    _code("saying", "OBSERVATION_FACT", "CATEGORY_CHAR", "Sprichwort-Verständnis")
    _code("picture", "OBSERVATION_FACT", "CATEGORY_CHAR", "Bildbeschreibung (Cookie Theft)")
    _code("session", "OBSERVATION_FACT", "CATEGORY_CHAR", "Session-Level Daten")
    _code("acoustic", "OBSERVATION_FACT", "CATEGORY_CHAR", "Akustische Stimm-Features (Praat)")
    _code("voicesample", "OBSERVATION_FACT", "CATEGORY_CHAR", "Stimmprobe (Vokal/Lesetext/Spontansprache)")

    # Patient group codes
    _code("Kontrolle", "OBSERVATION_FACT", "SS:SESSION:GROUP", "Kontrollgruppe")
    _code("Parkinson", "OBSERVATION_FACT", "SS:SESSION:GROUP", "Parkinson-Gruppe")
    _code("Sonstiges", "OBSERVATION_FACT", "SS:SESSION:GROUP", "Sonstige Gruppe")

    # Study status codes
    _code("planning", "STUDY_DIMENSION", "STATUS_CD", "In Planung")
    _code("active", "STUDY_DIMENSION", "STATUS_CD", "Aktiv")
    _code("completed", "STUDY_DIMENSION", "STATUS_CD", "Abgeschlossen")
    _code("suspended", "STUDY_DIMENSION", "STATUS_CD", "Ausgesetzt")

    return codes


# Mapping helpers for gender code conversion (used by import/export)
GENDER_TO_SNOMED = {
    "f": "SCTID: 407374003",
    "w": "SCTID: 407374003",  # German "weiblich"
    "m": "SCTID: 407375002",
    "d": "SCTID: 394744001",
}

SNOMED_TO_GENDER = {v: k for k, v in GENDER_TO_SNOMED.items() if k in ("f", "m", "d")}
