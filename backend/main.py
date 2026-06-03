import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config import settings
from db.database import Base, engine, UserBase, user_engine, UserSessionLocal
from middleware.logging_middleware import RequestIdFilter, LoggingMiddleware


def configure_logging():
    from logging.handlers import TimedRotatingFileHandler

    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(request_id)s] %(name)s %(levelname)s %(message)s")
    rid_filter = RequestIdFilter()

    root = logging.getLogger()
    root.setLevel(log_level)

    # 1. Console handler (for docker logs)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(fmt)
    console.addFilter(rid_filter)
    root.addHandler(console)

    # 2. app.log — everything INFO+
    app_handler = TimedRotatingFileHandler(
        str(log_dir / "app.log"), when="midnight", backupCount=settings.LOG_RETENTION_DAYS
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(fmt)
    app_handler.addFilter(rid_filter)
    root.addHandler(app_handler)

    # 3. error.log — WARNING+ only
    err_handler = TimedRotatingFileHandler(
        str(log_dir / "error.log"), when="midnight", backupCount=settings.LOG_RETENTION_DAYS
    )
    err_handler.setLevel(logging.WARNING)
    err_handler.setFormatter(fmt)
    err_handler.addFilter(rid_filter)
    root.addHandler(err_handler)

    # Suppress noisy loggers
    for name in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def cleanup_old_logs():
    """Remove rotated log files older than LOG_RETENTION_DAYS."""
    if not settings.LOG_CLEANUP_ENABLED:
        return
    logger = logging.getLogger(__name__)
    log_dir = Path(settings.LOG_DIR)
    if not log_dir.exists():
        return
    cutoff = time.time() - settings.LOG_RETENTION_DAYS * 86400
    count = 0
    try:
        for f in log_dir.iterdir():
            if f.is_file() and ".log." in f.name and f.stat().st_mtime < cutoff:
                f.unlink()
                count += 1
        if count:
            logger.info("Log cleanup: %d old files removed", count)
    except Exception:
        logger.warning("Log cleanup failed", exc_info=True)


def seed_users():
    """Seed admin + test user from env vars if users table is empty."""
    from db.user_models import User  # noqa: ensure model is registered
    from service.auth_service import pwd_context

    logger = logging.getLogger(__name__)
    db = UserSessionLocal()
    try:
        if db.query(User).count() == 0:
            # Admin user (from env vars)
            admin = User(
                username=settings.ADMIN_USERNAME,
                hashed_password=pwd_context.hash(settings.ADMIN_PASSWORD),
                is_admin=True,
            )
            db.add(admin)

            # Test user (from env vars) — only when DEV_AUTOLOGIN is enabled
            if settings.DEV_AUTOLOGIN and settings.TEST_USERNAME and settings.TEST_PASSWORD:
                standard = User(
                    username=settings.TEST_USERNAME,
                    hashed_password=pwd_context.hash(settings.TEST_PASSWORD),
                    is_admin=False,
                )
                db.add(standard)
                logger.info("Seeded users: %s (admin), %s (test)", settings.ADMIN_USERNAME, settings.TEST_USERNAME)
            else:
                logger.info("Seeded user: %s (admin)", settings.ADMIN_USERNAME)

            db.commit()
    finally:
        db.close()


def ensure_users():
    """Ensure admin and test users exist on every server start."""
    from db.user_models import User
    from service.auth_service import pwd_context

    logger = logging.getLogger(__name__)
    db = UserSessionLocal()
    try:
        # Ensure admin user exists and has is_admin=True
        admin_user = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if not admin_user:
            admin_user = User(
                username=settings.ADMIN_USERNAME,
                hashed_password=pwd_context.hash(settings.ADMIN_PASSWORD),
                is_admin=True,
            )
            db.add(admin_user)
            logger.info("Created missing admin user: %s", settings.ADMIN_USERNAME)
        elif not admin_user.is_admin:
            admin_user.is_admin = True
            logger.info("Upgraded %s to admin", settings.ADMIN_USERNAME)

        # Ensure test user exists (when DEV_AUTOLOGIN + credentials configured)
        if settings.DEV_AUTOLOGIN and settings.TEST_USERNAME and settings.TEST_PASSWORD:
            test_user = db.query(User).filter(User.username == settings.TEST_USERNAME).first()
            if not test_user:
                test_user = User(
                    username=settings.TEST_USERNAME,
                    hashed_password=pwd_context.hash(settings.TEST_PASSWORD),
                    is_admin=False,
                )
                db.add(test_user)
                logger.info("Created missing test user: %s", settings.TEST_USERNAME)

        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Speech DB — create base tables and run star schema migrations
    Base.metadata.create_all(bind=engine)

    from db.migrations.migration_manager import run_pending_migrations
    run_pending_migrations(engine)

    # User DB
    import db.user_models  # noqa: ensure models are registered
    UserBase.metadata.create_all(bind=user_engine)
    # Migration: add is_admin column to users if missing
    with user_engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(users)")).fetchall()]
        if "is_admin" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
        conn.commit()
    seed_users()
    ensure_users()
    cleanup_old_logs()

    yield


def create_app() -> FastAPI:
    configure_logging()

    application = FastAPI(lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:9011",
            "https://speechscribe-de.firebaseapp.com",
            settings.FRONTEND_URL,
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    application.add_middleware(LoggingMiddleware)

    from routers import auth, analysis, version, status, data, users, form_config, acoustic

    application.include_router(auth.router)
    application.include_router(analysis.router)
    application.include_router(version.router)
    application.include_router(status.router)
    application.include_router(data.router)
    application.include_router(users.router)
    application.include_router(form_config.router)
    application.include_router(acoustic.router)

    if settings.DEBUG:
        from routers import debug
        application.include_router(debug.router)
        logging.getLogger(__name__).warning("Debug-Endpoints aktiviert — nicht fuer Produktion geeignet")

    return application


app = create_app()
