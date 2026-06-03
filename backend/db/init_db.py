"""
Database initialization utility.

Not used at runtime — tables are created via lifespan in main.py.
Run standalone only for manual re-initialization of the speech DB.
"""
from pathlib import Path
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from .database import Base

logger = logging.getLogger(__name__)


def init_db():
    try:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Appdata directory checked/created at: %s", db_dir.absolute())

        engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
        logger.info("Database engine created for %s", settings.DATABASE_URL)

        # Import star schema models to register them with Base
        import db.models_star  # noqa: F401

        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        from db.migrations.migration_manager import run_pending_migrations
        run_pending_migrations(engine)
        logger.info("Migrations applied successfully")

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Database session factory created")

        return SessionLocal
    except Exception as e:
        logger.error("Error initializing database: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    init_db()
    logger.info("Database initialized successfully!")
