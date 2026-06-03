"""Repository for CONCEPT_DIMENSION — medical/measurement vocabulary."""

import logging

from sqlalchemy.orm import Session

from ..models_star import ConceptDimension
from .base import BaseRepository

logger = logging.getLogger(__name__)


class ConceptRepository(BaseRepository[ConceptDimension]):

    def __init__(self, session: Session):
        super().__init__(session, ConceptDimension, "CONCEPT_CD")

    def find_by_code(self, concept_cd: str) -> ConceptDimension | None:
        return (self.session.query(ConceptDimension)
                .filter(ConceptDimension.CONCEPT_CD == concept_cd)
                .first())

    def find_by_category(self, category: str) -> list[ConceptDimension]:
        return (self.session.query(ConceptDimension)
                .filter(ConceptDimension.CATEGORY_CHAR == category)
                .all())

    def find_by_path_prefix(self, path_prefix: str) -> list[ConceptDimension]:
        return (self.session.query(ConceptDimension)
                .filter(ConceptDimension.CONCEPT_PATH.like(f"{path_prefix}%"))
                .all())

    def upsert(self, data: dict) -> ConceptDimension:
        """Insert or update a concept by CONCEPT_CD."""
        existing = self.find_by_code(data["CONCEPT_CD"])
        if existing:
            for key, value in data.items():
                if key != "CONCEPT_CD" and hasattr(existing, key):
                    setattr(existing, key, value)
            self.session.flush()
            return existing
        return self.create(data)

    def bulk_upsert(self, concepts: list[dict]) -> int:
        """Upsert multiple concepts. Returns count of new concepts created."""
        created = 0
        for concept_data in concepts:
            existing = self.find_by_code(concept_data["CONCEPT_CD"])
            if not existing:
                self.create(concept_data)
                created += 1
            else:
                for key, value in concept_data.items():
                    if key != "CONCEPT_CD" and hasattr(existing, key):
                        setattr(existing, key, value)
        self.session.flush()
        return created
