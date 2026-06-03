import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_user_db
from db.user_models import User as DBUser
from service.auth_service import (
    Token, User, authenticate_user, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES,
)
from service.encryption_service import encrypt_api_key

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


class OpenAIKeyRequest(BaseModel):
    api_key: str


def _get_db_user(username: str, db: Session) -> DBUser:
    db_user = db.query(DBUser).filter(DBUser.username == username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    return db_user


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_user_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning("Login failed: user=%s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzername oder Passwort falsch",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "is_admin": user.is_admin},
        expires_delta=access_token_expires,
    )
    logger.info("Login successful: user=%s", user.username)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/user/me")
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_user_db),
):
    db_user = _get_db_user(current_user.username, db)
    return {
        "username": db_user.username,
        "is_active": db_user.is_active,
        "is_admin": db_user.is_admin or False,
        "has_openai_key": bool(db_user.encrypted_openai_key),
        "created_at": str(db_user.created_at) if db_user.created_at else None,
        "updated_at": str(db_user.updated_at) if db_user.updated_at else None,
    }


@router.put("/user/openai-key")
async def set_openai_key(
    body: OpenAIKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_user_db),
):
    db_user = _get_db_user(current_user.username, db)
    db_user.encrypted_openai_key = encrypt_api_key(body.api_key)
    db.commit()
    logger.info("OpenAI key updated: user=%s", current_user.username)
    return {"status": "ok", "message": "API-Key gespeichert"}


@router.get("/user/openai-key/status")
async def openai_key_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_user_db),
):
    db_user = _get_db_user(current_user.username, db)
    return {"has_key": bool(db_user.encrypted_openai_key)}


@router.delete("/user/openai-key")
async def delete_openai_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_user_db),
):
    db_user = _get_db_user(current_user.username, db)
    db_user.encrypted_openai_key = None
    db.commit()
    logger.info("OpenAI key deleted: user=%s", current_user.username)
    return {"status": "ok", "message": "API-Key geloescht"}
