from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import shutil
import os
import logging
import asyncio
import uuid
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from faster_whisper import WhisperModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Whisper Transcription API")

# Model will be loaded on first use
model = None

# Job storage for async operations
jobs = {}
jobs_lock = threading.Lock()

# Thread pool for transcription tasks
executor = ThreadPoolExecutor(max_workers=1)

def get_model():
    """Load model on first use (lazy loading)"""
    global model
    if model is None:
        model = WhisperModel("small", device="cpu", compute_type="int8")
    return model

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = None):
    """
    Transcribe an audio file.

    Supports: mp3, wav, m4a, flac, ogg, etc.

    Parameters:
    - file: Audio file to transcribe
    - language: Optional language code (e.g., 'en', 'es', 'fr'). If not set, language is auto-detected.
    """
    try:
        # Save uploaded file temporarily
        temp_dir = Path("./temp")
        temp_dir.mkdir(exist_ok=True)

        temp_file = temp_dir / file.filename

        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Load model
        whisper_model = get_model()

        # Transcribe with optional language parameter
        if language:
            logger.info(f"Transcribing with forced language: {language}")
            segments, info = whisper_model.transcribe(
                str(temp_file),
                language=language,
                vad_filter=True
            )
        else:
            logger.info("Transcribing with auto-detected language (VAD enabled)")
            segments, info = whisper_model.transcribe(
                str(temp_file),
                vad_filter=True
            )

        # Log detected language info
        logger.info(f"Detected language: {info.language}, Probability: {info.language_probability:.2%}")

        # Log all language candidates for debugging
        if hasattr(info, 'all_language_probs') and info.all_language_probs:
            logger.info("Top 5 language candidates:")
            for lang, prob in info.all_language_probs[:5]:
                logger.info(f"  {lang}: {prob:.2%}")

        # Convert segments iterator to list and collect results
        segments_list = list(segments)
        transcript = " ".join([seg.text for seg in segments_list])
        segments_data = [
            {
                "id": idx,
                "start": seg.start,
                "end": seg.end,
                "text": seg.text
            }
            for idx, seg in enumerate(segments_list)
        ]

        # Cleanup
        os.remove(temp_file)

        # Build response with all language candidates for debugging
        response = {
            "success": True,
            "transcript": transcript,
            "language": info.language,
            "language_probability": round(info.language_probability, 4),
            "segments": segments_data
        }

        # Include all language candidates if available
        if hasattr(info, 'all_language_probs') and info.all_language_probs:
            response["all_language_candidates"] = [
                {"language": lang, "probability": round(prob, 4)}
                for lang, prob in info.all_language_probs[:10]
            ]

        return JSONResponse(response)

    except Exception as e:
        # Cleanup on error
        if temp_file.exists():
            os.remove(temp_file)

        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe-async")
async def transcribe_async(file: UploadFile = File(...), language: str = None):
    """
    Submit audio file for asynchronous transcription.

    Returns a job_id that can be used to poll for results.
    Recommended for audio files > 30 minutes.

    Parameters:
    - file: Audio file to transcribe
    - language: Optional language code (e.g., 'en', 'es', 'fr'). If not set, language is auto-detected.

    Response:
    - job_id: Unique identifier to check transcription status
    - status: 'queued'
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())

        # Save uploaded file temporarily
        temp_dir = Path("./temp")
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / f"{job_id}_{file.filename}"

        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Store job status
        jobs[job_id] = {
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "filename": file.filename,
            "language_requested": language
        }

        logger.info(f"Queued transcription job {job_id} for file {file.filename}")

        # Start transcription in thread pool (keeps API responsive)
        executor.submit(process_transcription_async, job_id, temp_file, language)

        return JSONResponse({
            "job_id": job_id,
            "status": "queued",
            "check_status_url": f"/transcribe-status/{job_id}"
        }, status_code=202)

    except Exception as e:
        logger.error(f"Error queuing transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def process_transcription_async(job_id: str, file_path: Path, language: str = None):
    """Background task for async transcription (runs in thread pool)"""
    try:
        logger.info(f"Starting transcription for job {job_id}")
        with jobs_lock:
            jobs[job_id]["status"] = "processing"
            jobs[job_id]["started_at"] = datetime.utcnow().isoformat()

        # Load model
        whisper_model = get_model()

        # Transcribe with optional language parameter
        if language:
            logger.info(f"Job {job_id}: Transcribing with forced language: {language}")
            segments, info = whisper_model.transcribe(
                str(file_path),
                language=language,
                vad_filter=True
            )
        else:
            logger.info(f"Job {job_id}: Transcribing with auto-detected language (VAD enabled)")
            segments, info = whisper_model.transcribe(
                str(file_path),
                vad_filter=True
            )

        # Log detected language info
        logger.info(f"Job {job_id}: Detected language: {info.language}, Probability: {info.language_probability:.2%}")

        # Convert segments iterator to list and collect results
        segments_list = list(segments)
        transcript = " ".join([seg.text for seg in segments_list])
        segments_data = [
            {
                "id": idx,
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text
            }
            for idx, seg in enumerate(segments_list)
        ]

        # Build result
        result = {
            "success": True,
            "transcript": transcript,
            "language": info.language,
            "language_probability": round(info.language_probability, 4),
            "segments": segments_data
        }

        # Include all language candidates if available
        if hasattr(info, 'all_language_probs') and info.all_language_probs:
            result["all_language_candidates"] = [
                {"language": lang, "probability": round(prob, 4)}
                for lang, prob in info.all_language_probs[:10]
            ]

        # Update job with results (thread-safe)
        with jobs_lock:
            jobs[job_id].update({
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                **result
            })

        logger.info(f"Job {job_id}: Transcription completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id}: Transcription error - {str(e)}")
        with jobs_lock:
            jobs[job_id].update({
                "status": "error",
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat()
            })

    finally:
        # Cleanup file
        if file_path.exists():
            try:
                os.remove(file_path)
                logger.info(f"Job {job_id}: Cleaned up temporary file")
            except Exception as e:
                logger.warning(f"Job {job_id}: Failed to cleanup file - {str(e)}")

@app.get("/transcribe-status/{job_id}")
async def transcribe_status(job_id: str):
    """
    Check the status of a transcription job.

    Parameters:
    - job_id: The job ID returned from /transcribe-async

    Response statuses:
    - queued: Job is waiting to be processed
    - processing: Job is currently transcribing
    - completed: Job finished successfully (includes transcript and metadata)
    - error: Job failed (includes error message)
    - not_found: Job ID does not exist
    """
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        return JSONResponse(dict(jobs[job_id]))

@app.get("/transcribe-jobs")
async def list_jobs():
    """
    List all transcription jobs (for debugging).

    Returns a summary of all jobs with their current status.
    """
    with jobs_lock:
        return JSONResponse({
            "total_jobs": len(jobs),
            "jobs": {
                job_id: {
                    "status": job.get("status"),
                    "filename": job.get("filename"),
                    "created_at": job.get("created_at"),
                    "completed_at": job.get("completed_at")
                }
                for job_id, job in jobs.items()
            }
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
