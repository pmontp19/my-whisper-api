# Whisper Transcription API

A high-performance FastAPI-based audio transcription service powered by `faster-whisper` for automatic speech recognition (ASR).

## Features

- **4x Faster Transcription** — Optimized with `faster-whisper` using CTranslate2
- **Auto Language Detection** — Automatically detects the language of the audio
- **Multi-language Support** — Supports 99+ languages including Spanish, English, French, etc.
- **VAD Filtering** — Voice Activity Detection removes silence for cleaner transcription
- **Optional Language Parameter** — Explicitly specify language if needed
- **Language Candidates** — Returns top 10 language candidates for debugging
- **Word-level Timestamps** — Segments include start/end times for each phrase
- **INT8 Quantization** — Lower memory footprint without sacrificing accuracy
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

### Transcribe Audio

Transcribe an audio file with auto-detected language:

```bash
curl -X POST -F "file=@audio.mp3" http://localhost:8000/transcribe
```

Transcribe with explicit language (Spanish):

```bash
curl -X POST -F "file=@audio.mp3" -F "language=es" http://localhost:8000/transcribe
```

Response:
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

## Parameters

### `/transcribe` Endpoint

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | Yes | Audio file (mp3, wav, m4a, flac, ogg, etc.) |
| `language` | String | No | Language code (e.g., 'en', 'es', 'fr'). If not set, language is auto-detected. |

## Supported Languages

Spanish, English, French, German, Italian, Portuguese, Chinese, Japanese, Korean, Russian, Arabic, Hindi, and 88+ more.

## Performance

| Metric | Value |
|--------|-------|
| Image Size | 2.09 GB |
| Model | faster-whisper v1.2.0 |
| Compute Type | INT8 (quantized) |
| Speed | ~4x faster than openai-whisper |
| Language Detection | 84%+ accuracy with VAD |

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
