import logging

from fastapi import APIRouter

from config import settings
from form_config import patient_form_fields

logger = logging.getLogger(__name__)

router = APIRouter(tags=["config"])


@router.get("/config/patient-form")
def get_patient_form_config():
    """Return the patient form field configuration."""
    return {"fields": patient_form_fields()}


@router.get("/config/client")
def get_client_config():
    """Public endpoint: return client-relevant configuration flags."""
    cfg = {
        "dev_autologin": settings.DEV_AUTOLOGIN,
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
    }
    if settings.DEV_AUTOLOGIN and settings.TEST_USERNAME and settings.TEST_PASSWORD:
        cfg["test_username"] = settings.TEST_USERNAME
        cfg["test_password"] = settings.TEST_PASSWORD
    return cfg
