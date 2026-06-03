import logging

from sqlalchemy.orm import Session

from db.user_models import User
from service.encryption_service import decrypt_api_key

logger = logging.getLogger(__name__)


def get_openai_api_key(username: str, user_db: Session) -> str:
    """Resolve OpenAI API key from user DB or raise."""
    user = user_db.query(User).filter(User.username == username).first()
    if user and user.encrypted_openai_key:
        try:
            return decrypt_api_key(user.encrypted_openai_key)
        except Exception as e:
            logger.error("Failed to decrypt API key for user %s: %s", username, e)

    raise ValueError("Kein OpenAI API-Key konfiguriert. Bitte Key in den Einstellungen hinterlegen.")
