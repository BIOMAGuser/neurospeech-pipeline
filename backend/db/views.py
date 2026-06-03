"""
Database views for the i2b2 star schema.

The star schema views (patient_list_v2, patient_observations_v2) are created
by migration v003_create_star_views.py. This module is kept for backward
compatibility with main.py's lifespan call.
"""

from sqlalchemy import text
from .database import engine


def create_views():
    """No-op: star schema views are managed by the migration system."""
    pass
