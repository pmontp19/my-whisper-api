# Whisper Transcription API

A high-performance FastAPI-based audio transcription service powered by `faster-whisper` for automatic speech recognition (ASR).

## Features

- **4x Faster Transcription** — Optimized with `faster-whisper` using CTranslate2
- **Sync & Async API** — Synchronous for short files, asynchronous for long files (>30 min)
- **No Timeouts** — Async transcription handles files of any length without timeout
- **Auto Language Detection** — Automatically detects the language of the audio
- **Multi-language Support** — Supports 99+ languages including Spanish, English, French, Catalan, etc.
- **VAD Filtering** — Voice Activity Detection removes silence for cleaner transcription
- **Optional Language Parameter** — Explicitly specify language if needed
- **Language Candidates** — Returns top 10 language candidates for debugging
- **Word-level Timestamps** — Segments include start/end times for each phrase
- **INT8 Quantization** — Lower memory footprint without sacrificing accuracy
- **Job Management** — Track status of async jobs with full timestamps
- **Docker Support** — Pre-built Docker image available on Docker Hub

## Quick Start

### Using Docker

```bash
docker run -p 8000:8000 peremontpeo/whisper-api:latest
```

### Local Installation

```bash
pip install -r requirements.txt
python main.py
```

## API Endpoints

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok"
}
```

### Synchronous Transcription (For files < 30 minutes)

Transcribe an audio file with auto-detected language:

```bash
curl -X POST -F "file=@audio.mp3" http://localhost:8000/transcribe
```

Transcribe with explicit language:

```bash
curl -X POST -F "file=@audio.mp3" -F "language=es" http://localhost:8000/transcribe
```

Response (success):
```json
{
  "success": true,
  "transcript": "Full transcribed text...",
  "language": "es",
  "language_probability": 0.8405,
  "all_language_candidates": [
    {"language": "es", "probability": 0.8405},
    {"language": "it", "probability": 0.0736},
    {"language": "gl", "probability": 0.0316}
  ],
  "segments": [
    {
      "id": 0,
      "start": 0.24,
      "end": 7.48,
      "text": "First segment text"
    },
    {
      "id": 1,
      "start": 7.48,
      "end": 14.48,
      "text": "Second segment text"
    }
  ]
}
```

### Asynchronous Transcription (For files > 30 minutes)

Submit a long audio file for background transcription:

```bash
curl -X POST -F "file=@long_audio.mp3" http://localhost:8000/transcribe-async
```

Response (immediate, HTTP 202 Accepted):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "check_status_url": "/transcribe-status/550e8400-e29b-41d4-a716-446655440000"
}
```

**Check job status:**

```bash
curl http://localhost:8000/transcribe-status/550e8400-e29b-41d4-a716-446655440000
```

Status response (while processing):
```json
{
  "status": "processing",
  "created_at": "2025-10-21T10:20:00.000000",
  "started_at": "2025-10-21T10:20:05.000000",
  "filename": "long_audio.mp3",
  "language_requested": null
}
```

Status response (completed):
```json
{
  "status": "completed",
  "created_at": "2025-10-21T10:20:00.000000",
  "started_at": "2025-10-21T10:20:05.000000",
  "completed_at": "2025-10-21T10:45:30.000000",
  "filename": "long_audio.mp3",
  "language_requested": null,
  "success": true,
  "transcript": "Full transcribed text...",
  "language": "es",
  "language_probability": 0.8405,
  "segments": [...]
}
```

Status response (error):
```json
{
  "status": "error",
  "error": "Error message describing what went wrong",
  "completed_at": "2025-10-21T10:45:30.000000"
}
```

**List all jobs:**

```bash
curl http://localhost:8000/transcribe-jobs
```

## API Endpoints

| Endpoint | Method | Purpose | Timeout |
|----------|--------|---------|---------|
| `/health` | GET | Health check | N/A |
| `/transcribe` | POST | Sync transcription (short files) | 30 min |
| `/transcribe-async` | POST | Async transcription (long files) | None |
| `/transcribe-status/{job_id}` | GET | Check async job status | N/A |
| `/transcribe-jobs` | GET | List all jobs (debug) | N/A |

## Parameters

### `/transcribe` Endpoint (Synchronous)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | Yes | Audio file (mp3, wav, m4a, flac, ogg, etc.) |
| `language` | String | No | Language code (e.g., 'en', 'es', 'fr'). If not set, language is auto-detected. |

### `/transcribe-async` Endpoint (Asynchronous)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | Yes | Audio file (mp3, wav, m4a, flac, ogg, etc.) — no size limit |
| `language` | String | No | Language code (e.g., 'en', 'es', 'fr'). If not set, language is auto-detected. |

## n8n Integration

### Async Workflow Example

1. **Submit Job Node** (HTTP Request):
   - URL: `http://whisper-api:8000/transcribe-async`
   - Method: POST
   - Body: Binary file
   - Expected response: `job_id`

2. **Wait Node**: Sleep for 60 seconds

3. **Poll Status Node** (HTTP Request):
   - URL: `http://whisper-api:8000/transcribe-status/{{ $node["Submit Job"].json.job_id }}`
   - Method: GET

4. **Check Status Node** (Condition):
   - If status == "completed" → extract transcript
   - If status == "processing" → loop back to Wait Node
   - If status == "error" → handle error

This workflow handles files of any length without timeout issues!

## Supported Languages

Spanish, English, French, German, Italian, Portuguese, Chinese, Japanese, Korean, Russian, Arabic, Hindi, and 88+ more.

## Performance

| Metric | Value |
|--------|-------|
| Image Size | 2.09 GB |
| Model | faster-whisper v1.2.0 (small) |
| Compute Type | INT8 (quantized) |
| Memory Usage | ~1.2GB idle, ~1.5GB during transcription |
| Speed | ~4x faster than openai-whisper |
| Language Detection | 84%+ accuracy with VAD |
| Max File Size | Unlimited (with async endpoint) |
| Timeout | Sync: 30 min, Async: None |

### Resource Requirements

- **Minimum:** 3.7GB RAM (tested on Hetzner CX21)
- **Recommended:** 8GB RAM (Hetzner CX31) for better headroom
- **CPU:** 2+ cores recommended for concurrent requests

## Technical Stack

- **Framework** — FastAPI
- **ASR Engine** — faster-whisper (CTranslate2 optimized)
- **Async** — Uvicorn ASGI server
- **Audio Processing** — FFmpeg
- **Containerization** — Docker

## Docker Hub

Image available at: `peremontpeo/whisper-api:latest`

## Repository

GitHub: https://github.com/pmontp19/my-whisper-api

## License

MIT
