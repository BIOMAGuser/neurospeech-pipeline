"""
v002: Seed CONCEPT_DIMENSION and CODE_LOOKUP with SpeechScribe vocabulary.
"""

import logging
from sqlalchemy.engine import Engine

from db.database import SessionLocal
from db.repositories.concept_repository import ConceptRepository
from db.models_star import CodeLookup
from db.seeds.concepts import get_concept_seeds, get_code_lookup_seeds

logger = logging.getLogger(__name__)


def up(engine: Engine):
    """Insert concept and code lookup seed data."""
    session = SessionLocal()
    try:
        # Seed concepts
        concept_repo = ConceptRepository(session)
        concepts = get_concept_seeds()
        created = concept_repo.bulk_upsert(concepts)
        logger.info("Seeded %d new concepts (total defined: %d)", created, len(concepts))

        # Seed code lookups
        code_seeds = get_code_lookup_seeds()
        codes_created = 0
        for code_data in code_seeds:
            existing = session.query(CodeLookup).filter(
                CodeLookup.CODE_CD == code_data["CODE_CD"]
            ).first()
            if not existing:
                session.add(CodeLookup(**code_data))
                codes_created += 1
        logger.info("Seeded %d new code lookups (total defined: %d)", codes_created, len(code_seeds))

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
