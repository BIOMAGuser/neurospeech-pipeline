"""
v006: Seed CONCEPT_DIMENSION and CODE_LOOKUP with acoustic feature vocabulary.

Adds 39 SS:ACOUSTIC:* concepts (F0, jitter, shimmer, HNR, MFCC-13) and the
"acoustic" CATEGORY_CHAR code. Idempotent — re-uses bulk_upsert from v002.
"""

import logging
from sqlalchemy.engine import Engine

from db.database import SessionLocal
from db.repositories.concept_repository import ConceptRepository
from db.models_star import CodeLookup
from db.seeds.concepts import get_concept_seeds, get_code_lookup_seeds

logger = logging.getLogger(__name__)


def up(engine: Engine):
    """Insert acoustic concept and code lookup seed data."""
    session = SessionLocal()
    try:
        concept_repo = ConceptRepository(session)
        concepts = get_concept_seeds()
        created = concept_repo.bulk_upsert(concepts)
        logger.info("v006: seeded %d new concepts (acoustic vocabulary added)", created)

        code_seeds = get_code_lookup_seeds()
        codes_created = 0
        for code_data in code_seeds:
            existing = session.query(CodeLookup).filter(
                CodeLookup.CODE_CD == code_data["CODE_CD"]
            ).first()
            if not existing:
                session.add(CodeLookup(**code_data))
                codes_created += 1
        logger.info("v006: seeded %d new code lookups", codes_created)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
