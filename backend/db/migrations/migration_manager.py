"""
Migration manager for the i2b2 star schema.

Tracks applied migrations in a _star_migrations meta-table.
Runs pending migrations in version order on startup.
"""

import importlib
import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Registry of all migrations in order
MIGRATIONS = [
    {"version": 1, "name": "create_star_schema", "module": "db.migrations.v001_create_star_schema"},
    {"version": 2, "name": "seed_concepts", "module": "db.migrations.v002_seed_concepts"},
    {"version": 3, "name": "create_star_views", "module": "db.migrations.v003_create_star_views"},
    {"version": 4, "name": "migrate_historical_data", "module": "db.migrations.v004_migrate_historical_data"},
    {"version": 5, "name": "drop_legacy_tables", "module": "db.migrations.v005_drop_legacy_tables"},
    {"version": 6, "name": "seed_acoustic_concepts", "module": "db.migrations.v006_seed_acoustic_concepts"},
    {"version": 7, "name": "voicesample_category", "module": "db.migrations.v007_voicesample_category"},
]


def _ensure_migration_table(engine: Engine):
    """Create the migrations tracking table if it doesn't exist."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS _star_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """))
        conn.commit()


def _get_applied_versions(engine: Engine) -> set[int]:
    """Get set of already-applied migration versions."""
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT version FROM _star_migrations")).fetchall()
    return {row[0] for row in rows}


def _mark_applied(engine: Engine, version: int, name: str):
    """Record a migration as applied."""
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO _star_migrations (version, name) VALUES (:v, :n)"),
            {"v": version, "n": name},
        )
        conn.commit()


def run_pending_migrations(engine: Engine):
    """Run all pending star-schema migrations in order."""
    _ensure_migration_table(engine)
    applied = _get_applied_versions(engine)

    pending = [m for m in MIGRATIONS if m["version"] not in applied]
    if not pending:
        logger.info("Star schema: all %d migrations already applied", len(MIGRATIONS))
        return

    logger.info("Star schema: %d pending migration(s)", len(pending))

    for migration in sorted(pending, key=lambda m: m["version"]):
        version = migration["version"]
        name = migration["name"]
        module_path = migration["module"]

        logger.info("Running migration v%03d: %s", version, name)
        try:
            mod = importlib.import_module(module_path)
            mod.up(engine)
            _mark_applied(engine, version, name)
            logger.info("Migration v%03d completed successfully", version)
        except Exception:
            logger.exception("Migration v%03d FAILED: %s", version, name)
            raise
