import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, UploadFile, Form, Depends, HTTPException, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db, get_user_db
from analysis.task_registry import get_task_def, valid_task_names
from service.auth_service import get_current_user, User
from service.openai_key_service import get_openai_api_key
from service.observation_builder import write_to_star_schema

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])


class TextAnalysisRequest(BaseModel):
    transcript: str
    taskType: str
    attemptId: str


class AnalysisResponse(BaseModel):
    processedAt: str
    task: str
    attemptId: str
    metrics: Dict[str, Any]


@router.post("/analyze_text")
async def analyze_text_endpoint(
    request_data: TextAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_db: Session = Depends(get_user_db),
):
    transcript = request_data.transcript
    taskType = request_data.taskType
    attemptId = request_data.attemptId

    task_def = get_task_def(taskType)
    if not task_def:
        raise HTTPException(status_code=422, detail=f"Ungueltiger Aufgabentyp: {taskType}")

    api_key = None
    if task_def.requires_api_key:
        try:
            api_key = get_openai_api_key(current_user.username, user_db)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    metrics = task_def.analyze(transcript, api_key=api_key)

    return {
        "processedAt": datetime.utcnow().isoformat() + "Z",
        "task": taskType,
        "attemptId": attemptId,
        "transcript": transcript,
        "metrics": metrics,
    }


@router.post("/analyze")
async def analyze_audio(
    audio: UploadFile = File(...),
    taskType: str = Form(...),
    attemptId: str = Form(...),
    duration_seconds: Optional[float] = Form(None),
    patient_id: Optional[str] = Form(None),
    test_date: Optional[str] = Form(None),
    group: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    moca_score: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    session_analysis_id: Optional[str] = Form(None),
    save_to_database: Optional[str] = Form("true"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    user_db: Session = Depends(get_user_db),
):
    audio_uuid = None
    try:
        try:
            api_key = get_openai_api_key(current_user.username, user_db)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        logger.info("Starting audio analysis for task: %s", taskType)
        task_def = get_task_def(taskType)
        if not task_def:
            raise HTTPException(status_code=422, detail=f"Ungueltiger Aufgabentyp: {taskType}")
        logger.info("Session Analysis ID: %s", session_analysis_id)
        logger.info("Save to database: %s", save_to_database)

        should_save_to_db = (save_to_database or "").lower() == "true"

        if should_save_to_db:
            if not patient_id:
                raise HTTPException(status_code=422, detail="patient_id ist erforderlich fuer Datenbank-Speicherung")
            if not test_date:
                test_date = datetime.now().strftime("%Y-%m-%d")
                logger.warning("No test date provided, using default: %s", test_date)
            # Validate dates early
            try:
                datetime.strptime(test_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=422, detail="Ungueltiges Testdatum (erwartet: YYYY-MM-DD)")
            if birth_date:
                try:
                    datetime.strptime(birth_date, "%Y-%m-%d")
                except ValueError:
                    raise HTTPException(status_code=422, detail="Ungueltiges Geburtsdatum (erwartet: YYYY-MM-DD)")
            parsed_moca = None
            if moca_score:
                try:
                    parsed_moca = int(moca_score)
                except ValueError:
                    raise HTTPException(status_code=422, detail="Ungueltiger MoCa-Wert (muss eine Zahl sein)")

            logger.info("Using patient ID: %s, test date: %s", patient_id, test_date)
        else:
            logger.info("Skipping database operations - save_to_database is false")

        audio_bytes = await audio.read()
        logger.info("Audio file read successfully, size: %d bytes", len(audio_bytes))

        from service.whisper_service import whisper_transcribe_verbose

        loop = asyncio.get_event_loop()

        # Run transcription and MP3 conversion in parallel
        transcribe_future = loop.run_in_executor(
            None, whisper_transcribe_verbose, audio_bytes, api_key, taskType
        )

        mp3_future = None
        if should_save_to_db:
            from service.audio_storage_service import convert_and_save_mp3
            mp3_future = loop.run_in_executor(None, convert_and_save_mp3, audio_bytes, None)

        transcript = await transcribe_future

        if mp3_future is not None:
            try:
                audio_uuid = await mp3_future
            except Exception as e:
                logger.warning("MP3 conversion failed (non-fatal): %s", e)

        logger.info("Enhanced transcription completed (task: %s), length: %d characters", taskType, len(transcript))

        metrics = task_def.analyze(transcript, api_key=api_key)

        logger.info("Analysis completed for task %s", taskType)

        star_result = None
        if should_save_to_db:
            star_result = write_to_star_schema(
                db,
                patient_id=patient_id,
                birth_date=birth_date,
                gender=gender,
                session_analysis_id=session_analysis_id,
                test_date=test_date,
                moca_score=parsed_moca,
                group=group,
                notes=notes,
                task_type=taskType,
                metrics=metrics,
                transcript=transcript,
                audio_uuid=audio_uuid,
                audio_duration=duration_seconds,
                attempt_id=attemptId,
                username=current_user.username,
            )
            db.commit()
            logger.info(
                "Star schema write: patient_num=%s, encounter_num=%s, observations=%d",
                star_result["patient_num"],
                star_result["encounter_num"],
                star_result["observation_count"],
            )

        response_data = {
            "processedAt": datetime.utcnow().isoformat(),
            "task": taskType,
            "attemptId": attemptId,
            "transcript": transcript,
            "metrics": metrics,
        }

        if should_save_to_db and star_result:
            response_data.update({
                "db_id": star_result["encounter_num"],
                "patient_id": star_result["patient_num"],
                "analysis_id": star_result["encounter_num"],
                "trial_id": star_result["encounter_num"],
            })

        return response_data

    except HTTPException:
        db.rollback()
        if audio_uuid:
            from service.audio_storage_service import delete_mp3
            delete_mp3(audio_uuid)
        raise
    except Exception as e:
        db.rollback()
        if audio_uuid:
            from service.audio_storage_service import delete_mp3
            delete_mp3(audio_uuid)
        logger.error("Error in analyze_audio: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Interner Fehler bei der Audioverarbeitung")
