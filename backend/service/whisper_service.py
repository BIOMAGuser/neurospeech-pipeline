import io
import logging
import time

from openai import OpenAI

from prompt_config import whisper_cfg

logger = logging.getLogger(__name__)


def detect_audio_format(audio_bytes: bytes) -> str:
    if not audio_bytes:
        return "wav"

    header = audio_bytes[:12]

    if header.startswith(b'RIFF') and b'WAVE' in header:
        return "wav"
    if header.startswith(b'ID3') or header.startswith(b'\xff\xfb') or header.startswith(b'\xff\xf3'):
        return "mp3"
    if header.startswith(b'fLaC'):
        return "flac"
    if header.startswith(b'OggS'):
        return "ogg"
    if header.startswith(b'\x1a\x45\xdf\xa3'):
        return "webm"
    if b'ftyp' in header[:12] and (b'M4A ' in header or b'mp42' in header):
        return "m4a"

    return "wav"


def _make_audio_buffer(audio_bytes: bytes) -> io.BytesIO:
    buf = io.BytesIO(audio_bytes)
    detected_format = detect_audio_format(audio_bytes)
    buf.name = f"audio.{detected_format}"
    logger.info("Detected audio format: %s (file size: %d bytes)", detected_format, len(audio_bytes))
    return buf


def whisper_transcribe_medical(audio_bytes: bytes, api_key: str, task_type: str = "general", fmt: str = "text") -> str:
    cfg = whisper_cfg()
    prompts = cfg["prompts"]

    client = OpenAI(api_key=api_key)
    buf = _make_audio_buffer(audio_bytes)

    start = time.perf_counter()
    resp = client.audio.transcriptions.create(
        file=buf,
        model=cfg["model"],
        language=cfg["language"],
        prompt=prompts.get(task_type, prompts["general"]),
        temperature=cfg["temperature"],
        response_format=fmt,
    )

    result = resp if isinstance(resp, str) else (resp.text if hasattr(resp, "text") else resp["text"])
    elapsed = time.perf_counter() - start
    logger.info("Whisper response: %d chars in %.2fs", len(result), elapsed)
    return result


def whisper_transcribe_verbose(audio_bytes: bytes, api_key: str, task_type: str = "general") -> str:
    cfg = whisper_cfg()
    verbose_prompts = cfg["verbose_prompts"]

    buf = _make_audio_buffer(audio_bytes)

    client = OpenAI(api_key=api_key)
    try:
        start = time.perf_counter()
        resp = client.audio.transcriptions.create(
            file=buf,
            model=cfg["model"],
            language=cfg["language"],
            prompt=verbose_prompts.get(task_type, verbose_prompts["general"]),
            temperature=cfg["temperature"],
            response_format="verbose_json",
        )

        if hasattr(resp, "text"):
            result = resp.text
        elif isinstance(resp, dict) and "text" in resp:
            result = resp["text"]
        else:
            result = str(resp)

        elapsed = time.perf_counter() - start
        logger.info("Whisper response: %d chars in %.2fs", len(result), elapsed)
        return result

    except Exception as e:
        logger.warning("Verbose transcription failed, falling back to standard: %s", e)
        return whisper_transcribe_medical(audio_bytes, api_key, task_type, "text")
