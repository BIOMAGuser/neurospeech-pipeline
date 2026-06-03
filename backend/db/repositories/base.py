"""
Generic base repository with CRUD operations and criteria-based queries.

Follows the BEST Scientific DB Manager repository pattern, adapted for
Python/SQLAlchemy. Provides parameterized queries to prevent SQL injection.
"""

import logging
from typing import TypeVar, Generic, Type, Any

from sqlalchemy import asc, desc, func, and_, or_
from sqlalchemy.orm import Session

T = TypeVar("T")
logger = logging.getLogger(__name__)


class BaseRepository(Generic[T]):
    """Generic repository providing CRUD, search, and pagination."""

    def __init__(self, session: Session, model_class: Type[T], primary_key: str = None):
        self.session = session
        self.model = model_class
        self._pk_name = primary_key or self._detect_pk()

    def _detect_pk(self) -> str:
        """Auto-detect primary key column name."""
        mapper = self.model.__mapper__
        pk_cols = mapper.primary_key
        if pk_cols:
            return pk_cols[0].name
        return "id"

    # ── Read ──────────────────────────────────────────────────

    def find_by_id(self, id_value: Any) -> T | None:
        pk_col = getattr(self.model, self._pk_name)
        return self.session.query(self.model).filter(pk_col == id_value).first()

    def find_all(self, limit: int = 500, offset: int = 0,
                 order_by: str = None, order_direction: str = "ASC") -> list[T]:
        q = self.session.query(self.model)
        if order_by and hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            q = q.order_by(asc(col) if order_direction.upper() == "ASC" else desc(col))
        return q.offset(offset).limit(limit).all()

    def find_by_criteria(self, criteria: dict, limit: int = 500, offset: int = 0,
                         order_by: str = None, order_direction: str = "ASC") -> list[T]:
        q = self._apply_criteria(self.session.query(self.model), criteria)
        if order_by and hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            q = q.order_by(asc(col) if order_direction.upper() == "ASC" else desc(col))
        return q.offset(offset).limit(limit).all()

    def count_by_criteria(self, criteria: dict) -> int:
        q = self._apply_criteria(self.session.query(func.count()), criteria)
        return q.scalar() or 0

    def exists(self, criteria: dict) -> bool:
        q = self._apply_criteria(self.session.query(self.model), criteria)
        return q.first() is not None

    # ── Write ─────────────────────────────────────────────────

    def create(self, data: dict) -> T:
        entity = self.model(**data)
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, id_value: Any, data: dict) -> T | None:
        entity = self.find_by_id(id_value)
        if entity is None:
            return None
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        self.session.flush()
        return entity

    def update_by_criteria(self, criteria: dict, data: dict) -> int:
        q = self._apply_criteria(self.session.query(self.model), criteria)
        count = q.update(data, synchronize_session="fetch")
        self.session.flush()
        return count

    # ── Delete ────────────────────────────────────────────────

    def delete(self, id_value: Any) -> bool:
        entity = self.find_by_id(id_value)
        if entity is None:
            return False
        self.session.delete(entity)
        self.session.flush()
        return True

    def delete_by_criteria(self, criteria: dict) -> int:
        q = self._apply_criteria(self.session.query(self.model), criteria)
        count = q.delete(synchronize_session="fetch")
        self.session.flush()
        return count

    # ── Pagination ────────────────────────────────────────────

    def get_paginated(self, page: int = 1, page_size: int = 20,
                      criteria: dict = None, order_by: str = None,
                      order_direction: str = "ASC") -> dict:
        base_q = self.session.query(self.model)
        if criteria:
            base_q = self._apply_criteria(base_q, criteria)

        total_count = base_q.count()
        total_pages = max(1, (total_count + page_size - 1) // page_size)

        if order_by and hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            base_q = base_q.order_by(asc(col) if order_direction.upper() == "ASC" else desc(col))

        offset = (page - 1) * page_size
        items = base_q.offset(offset).limit(page_size).all()

        return {
            "items": items,
            "pagination": {
                "currentPage": page,
                "pageSize": page_size,
                "totalCount": total_count,
                "totalPages": total_pages,
                "hasNextPage": page < total_pages,
                "hasPreviousPage": page > 1,
            },
        }

    # ── Criteria Engine ───────────────────────────────────────

    def _apply_criteria(self, query, criteria: dict):
        """
        Apply criteria dict to query. Supports:
        - Simple equality: {"FIELD": value}
        - IN clause: {"FIELD": [val1, val2]}
        - Operators: {"FIELD": {"operator": ">", "value": 30}}
        - LIKE: {"FIELD": {"operator": "LIKE", "value": "%term%"}}
        - BETWEEN: {"FIELD": {"operator": "BETWEEN", "value": [min, max]}}
        - IS NULL: {"FIELD": None}
        """
        filters = []
        for field, value in criteria.items():
            if not hasattr(self.model, field):
                logger.warning("Criteria field %s not found on %s", field, self.model.__tablename__)
                continue

            col = getattr(self.model, field)

            if value is None:
                filters.append(col.is_(None))
            elif isinstance(value, list):
                filters.append(col.in_(value))
            elif isinstance(value, dict):
                op = value.get("operator", "=").upper()
                val = value.get("value")
                if op == "BETWEEN" and isinstance(val, (list, tuple)) and len(val) == 2:
                    filters.append(col.between(val[0], val[1]))
                elif op == "LIKE":
                    filters.append(col.like(val))
                elif op == "ILIKE":
                    filters.append(col.ilike(val))
                elif op == ">":
                    filters.append(col > val)
                elif op == ">=":
                    filters.append(col >= val)
                elif op == "<":
                    filters.append(col < val)
                elif op == "<=":
                    filters.append(col <= val)
                elif op == "!=":
                    filters.append(col != val)
                elif op == "IS NOT NULL":
                    filters.append(col.isnot(None))
                else:
                    filters.append(col == val)
            else:
                filters.append(col == value)

        if filters:
            query = query.filter(and_(*filters))

        return query
