import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from db.database import get_user_db
from db.user_models import User as DBUser
from service.auth_service import User, get_current_admin, pwd_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    username: str
    password: str
    is_admin: bool = False

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Passwort muss mindestens 8 Zeichen lang sein")
        return v


class UserUpdate(BaseModel):
    password: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


@router.get("")
def list_users(
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_user_db),
):
    users = db.query(DBUser).order_by(DBUser.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "is_active": u.is_active,
            "is_admin": u.is_admin or False,
            "has_openai_key": bool(u.encrypted_openai_key),
            "created_at": str(u.created_at) if u.created_at else None,
        }
        for u in users
    ]


@router.post("", status_code=201)
def create_user(
    body: UserCreate,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_user_db),
):
    if db.query(DBUser).filter(DBUser.username == body.username).first():
        raise HTTPException(status_code=409, detail="Benutzername existiert bereits")

    user = DBUser(
        username=body.username,
        hashed_password=pwd_context.hash(body.password),
        is_admin=body.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User created: %s (by admin: %s)", body.username, _admin.username)
    return {
        "id": user.id,
        "username": user.username,
        "is_active": user.is_active,
        "is_admin": user.is_admin or False,
    }


@router.put("/{user_id}")
def update_user(
    user_id: int,
    body: UserUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_user_db),
):
    user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")

    # Prevent admin from demoting or deactivating themselves
    if user.username == admin.username:
        if body.is_admin is not None and not body.is_admin:
            raise HTTPException(status_code=422, detail="Eigene Admin-Rechte kann man nicht entziehen")
        if body.is_active is not None and not body.is_active:
            raise HTTPException(status_code=422, detail="Eigenen Account kann man nicht deaktivieren")

    if body.password is not None:
        if len(body.password) < 8:
            raise HTTPException(status_code=422, detail="Passwort muss mindestens 8 Zeichen lang sein")
        user.hashed_password = pwd_context.hash(body.password)
    if body.is_admin is not None:
        user.is_admin = body.is_admin
    if body.is_active is not None:
        user.is_active = body.is_active

    db.commit()
    logger.info("User updated: %s (by admin: %s)", user.username, admin.username)
    return {
        "id": user.id,
        "username": user.username,
        "is_active": user.is_active,
        "is_admin": user.is_admin or False,
    }


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_user_db),
):
    user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    if user.username == admin.username:
        raise HTTPException(status_code=422, detail="Eigenen Account kann man nicht loeschen")

    username = user.username
    db.delete(user)
    db.commit()
    logger.info("User deleted: %s (by admin: %s)", username, admin.username)
    return {"status": "ok"}
