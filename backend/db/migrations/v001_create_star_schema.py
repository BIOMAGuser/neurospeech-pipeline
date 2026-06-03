"""
v001: Create all i2b2 star schema tables.

Note: Tables are already created by Base.metadata.create_all() in main.py
since models_star.py registers with the same Base. This migration exists
for version tracking only.
"""

import logging
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def up(engine: Engine):
    """No-op: star schema tables are created by Base.metadata.create_all()."""
    logger.info("Star schema tables created via Base.metadata.create_all()")
