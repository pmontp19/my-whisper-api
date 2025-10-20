from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import shutil
import os
import logging
from pathlib import Path
from faster_whisper import WhisperModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Whisper Transcription API")

# Model will be loaded on first use
model = None

def get_model():
    """Load model on first use (lazy loading)"""
    global model
    if model is None:
        model = WhisperModel("base", device="cpu", compute_type="int8")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
