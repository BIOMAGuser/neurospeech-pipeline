"""
v007: Introduce 'voicesample' CATEGORY_CHAR for acoustic-only audio
recordings (sustained vowels, read text, free speech), and migrate
the previously-imported MDVR-KCL demo trials away from the misleading
'picture' placeholder.

After this migration:
- SS:VOICESAMPLE:{TRANSCRIPT,AUDIO_UUID,AUDIO_DURATION} concepts exist.
- DEMO-MDVR-* trials carry CATEGORY_CHAR='voicesample' and the matching
  SS:VOICESAMPLE:* concept codes for transcript/audio_uuid/audio_duration.
- The acoustic OBSERVATION_FACT rows themselves stay on
  CATEGORY_CHAR='acoustic' (unchanged) — only the trial-anchor rows move.
"""

import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

from db.database import SessionLocal
from db.models_star import CodeLookup
from db.repositories.concept_repository import ConceptRepository
from db.seeds.concepts import get_code_lookup_seeds, get_concept_seeds

logger = logging.getLogger(__name__)

DEMO_PREFIX = "DEMO-MDVR-"

CONCEPT_RENAMES = {
    "SS:PICTURE:TRANSCRIPT": "SS:VOICESAMPLE:TRANSCRIPT",
    "SS:PICTURE:AUDIO_UUID": "SS:VOICESAMPLE:AUDIO_UUID",
    "SS:PICTURE:AUDIO_DURATION": "SS:VOICESAMPLE:AUDIO_DURATION",
}


def up(engine: Engine):
    """Seed new concepts and re-categorize existing DEMO trials."""
    # Guard against a multi-worker race: if another worker already committed
    # this migration, _star_migrations may not yet show it from this session
    # but the seeded concepts will already exist and a fresh INSERT would hit
    # the UNIQUE constraint.  Cheap pre-check on a known concept.
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT 1 FROM CONCEPT_DIMENSION WHERE CONCEPT_CD = :cd"),
            {"cd": "SS:VOICESAMPLE:AUDIO_UUID"},
        ).first()
    if existing:
        logger.info("v007: voicesample concepts already exist, skipping seed phase")
        # Fall through to the data-rename phase below — also idempotent because
        # the WHERE clauses match the OLD concept codes which are gone after
        # the first successful run.
    session = SessionLocal()
    try:
        if not existing:
            # 1. Seed the new concepts (idempotent)
            repo = ConceptRepository(session)
            created = repo.bulk_upsert(get_concept_seeds())
            logger.info("v007: seeded %d new concepts (voicesample vocabulary)", created)

            # 2. Seed the new CATEGORY_CHAR code lookup
            codes_added = 0
            for code_data in get_code_lookup_seeds():
                existing_code = (
                    session.query(CodeLookup)
                    .filter(CodeLookup.CODE_CD == code_data["CODE_CD"])
                    .first()
                )
                if not existing_code:
                    session.add(CodeLookup(**code_data))
                    codes_added += 1
            logger.info("v007: seeded %d new code lookups", codes_added)
            session.commit()

        # 3. Re-categorize DEMO trial-anchor rows: 'picture' -> 'voicesample'
        # Only OBSERVATION_FACT rows that belong to demo patients AND carry one
        # of the picture-specific anchor concepts (the audio_uuid/duration/transcript
        # rows). The acoustic-feature rows (CATEGORY_CHAR='acoustic') are left alone.
        with engine.begin() as conn:
            # Update CATEGORY_CHAR for the trial-anchor observations
            for old_cd, new_cd in CONCEPT_RENAMES.items():
                conn.execute(
                    text("""
                        UPDATE OBSERVATION_FACT
                        SET CONCEPT_CD = :new_cd,
                            CATEGORY_CHAR = 'voicesample',
                            UPDATE_DATE = datetime('now')
                        WHERE CONCEPT_CD = :old_cd
                          AND PATIENT_NUM IN (
                              SELECT PATIENT_NUM FROM PATIENT_DIMENSION
                              WHERE PATIENT_CD LIKE :prefix
                          )
                    """),
                    {"old_cd": old_cd, "new_cd": new_cd, "prefix": f"{DEMO_PREFIX}%"},
                )

        # 4. Count what got migrated for the log
        with engine.connect() as conn:
            n = conn.execute(
                text("""
                    SELECT COUNT(*) FROM OBSERVATION_FACT
                    WHERE CATEGORY_CHAR = 'voicesample'
                      AND PATIENT_NUM IN (
                          SELECT PATIENT_NUM FROM PATIENT_DIMENSION
                          WHERE PATIENT_CD LIKE :prefix
                      )
                """),
                {"prefix": f"{DEMO_PREFIX}%"},
            ).scalar()
        logger.info("v007: %d demo trial-anchor observations migrated to voicesample", n)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
