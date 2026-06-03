import base64
import hashlib
import logging

from cryptography.fernet import Fernet

from config import settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    secret = settings.ENCRYPTION_KEY or settings.JWT_SECRET_KEY
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt_api_key(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except Exception:
        logger.error("API key decryption failed — key was likely encrypted with a different secret")
        raise
