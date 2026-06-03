import io
import logging
import re
import uuid
from pathlib import Path

from pydub import AudioSegment

from service.whisper_service import detect_audio_format

logger = logging.getLogger(__name__)

_UUID_HEX_RE = re.compile(r"^[0-9a-f]{32}$")

# Derive MP3 directory from the database path (same appdata folder)
_MP3_DIR: Path | None = None


def _get_mp3_dir() -> Path:
    global _MP3_DIR
    if _MP3_DIR is None:
        from config import settings
        db_url = settings.DATABASE_URL
        # sqlite:////app/appdata/speech1.db -> /app/appdata
        db_path = db_url.replace("sqlite:///", "")
        appdata = Path(db_path).parent
        _MP3_DIR = appdata / "mp3"
        _MP3_DIR.mkdir(parents=True, exist_ok=True)
    return _MP3_DIR


def _safe_mp3_path(audio_uuid: str) -> Path | None:
    """Return a safe path inside the MP3 dir, or None if the UUID is invalid."""
    if not audio_uuid or not _UUID_HEX_RE.match(audio_uuid):
        return None
    path = _get_mp3_dir() / f"{audio_uuid}.mp3"
    # Resolve to catch any symlink tricks
    if not path.resolve().parent == _get_mp3_dir().resolve():
        return None
    return path


def convert_and_save_mp3(audio_bytes: bytes, source_format: str | None = None) -> str:
    """Convert audio bytes to MP3 and save. Returns the UUID."""
    if source_format is None:
        source_format = detect_audio_format(audio_bytes)

    audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=source_format)
    audio_uuid = uuid.uuid4().hex
    mp3_path = _get_mp3_dir() / f"{audio_uuid}.mp3"
    audio.export(str(mp3_path), format="mp3", bitrate="128k")
    logger.info("Saved MP3: %s (%.1f KB)", mp3_path.name, mp3_path.stat().st_size / 1024)
    return audio_uuid


def get_mp3_path(audio_uuid: str) -> str | None:
    """Return the file path if the MP3 exists, else None."""
    path = _safe_mp3_path(audio_uuid)
    if path is None:
        return None
    return str(path) if path.exists() else None


def delete_mp3(audio_uuid: str) -> bool:
    """Delete an MP3 file. Returns True if deleted. Never raises."""
    try:
        path = _safe_mp3_path(audio_uuid)
        if path is None:
            return False
        if path.exists():
            path.unlink()
            logger.info("Deleted MP3: %s", path.name)
            return True
        return False
    except Exception as e:
        logger.warning("Failed to delete MP3 %s: %s", audio_uuid, e)
        return False
