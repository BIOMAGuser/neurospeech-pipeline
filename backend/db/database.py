import logging
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

logger = logging.getLogger(__name__)

logger.info("Initializing database module")


def _ensure_db_dir(url: str):
    db_path = url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info("Created directory: %s", db_dir)


# ── Speech DB (Messdaten) ──────────────────────────────────
_ensure_db_dir(settings.DATABASE_URL)
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ── User DB (Nutzer, Einstellungen, API-Keys) ──────────────
_ensure_db_dir(settings.USER_DATABASE_URL)
user_engine = create_engine(settings.USER_DATABASE_URL, connect_args={"check_same_thread": False})
UserSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=user_engine)
UserBase = declarative_base()


# ── SQLite WAL mode for concurrent access ──────────────────
@event.listens_for(engine, "connect")
def set_sqlite_wal_speech(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


@event.listens_for(user_engine, "connect")
def set_sqlite_wal_user(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_db():
    db = UserSessionLocal()
    try:
        yield db
    finally:
        db.close()
