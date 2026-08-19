# HR-Presents ORIVOX

**ORIVOX — Local AI Voice Assistant**

ORIVOX is a local-first voice assistant by **HR-Presents**. Its real runtime pipeline is microphone audio → Faster-Whisper → local conversational model through Ollama → Kokoro speech → speaker playback. Conversation/account data is stored in an application-managed SQLite database.

## Architecture

- `orivox/app.py` — FastAPI application/API
- `orivox/db.py` — SQLite users, conversations, messages and settings
- `orivox/services.py` — lazy-loaded Whisper, local LLM and Kokoro runtime
- `orivox/config.py` — portable environment-aware configuration
- `run.py` — local launcher

The code deliberately separates STT, conversational AI and TTS so models can be upgraded independently.

## Windows setup

Requirements: Windows 10/11 x64, Python 3.11 recommended, working microphone/speaker, and Ollama for the default local conversational model.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
ollama pull qwen2.5:3b
python run.py
```

Open `http://127.0.0.1:8765/docs` for the API while the full desktop/web client is being integrated.

Models and the database are stored under `%LOCALAPPDATA%\ORIVOX` by default, never under a developer-specific path. Override with `ORIVOX_DATA_DIR`, `ORIVOX_MODEL_DIR`, `ORIVOX_DB_PATH`, `ORIVOX_WHISPER_MODEL`, `ORIVOX_LLM_MODEL`, `ORIVOX_OLLAMA_URL`, or `ORIVOX_PORT`.

## Privacy

Core speech recognition, conversation generation and speech synthesis are designed to execute locally. ORIVOX does not require cloud transcription for its basic pipeline. Raw microphone recordings are not persisted by the API.

## Current implementation status

This branch establishes the real backend foundation: hashed local accounts, SQLite persistence, dynamic history, Faster-Whisper transcription, Ollama-backed local AI, Kokoro synthesis, model status and portable configuration. The branded responsive client, settings/profile CRUD, installer assets and end-to-end packaged Windows validation must be completed and tested before ORIVOX is called production-complete.

Copyright (c) 2026 **HR-Presents**. All rights reserved.
