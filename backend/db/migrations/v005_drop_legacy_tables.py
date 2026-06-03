"""
v005: Drop legacy tables and views.

Removes the old patients/analyses/trials tables and the
patient_analysis_trials view now that all reads/writes use the star schema.
"""

import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def up(engine: Engine):
    """Drop legacy tables and views."""
    with engine.connect() as conn:
        conn.execute(text("DROP VIEW IF EXISTS patient_analysis_trials"))
        logger.info("Dropped view: patient_analysis_trials")

        conn.execute(text("DROP TABLE IF EXISTS trials"))
        logger.info("Dropped table: trials")

        conn.execute(text("DROP TABLE IF EXISTS analyses"))
        logger.info("Dropped table: analyses")

        conn.execute(text("DROP TABLE IF EXISTS patients"))
        logger.info("Dropped table: patients")

        conn.commit()
