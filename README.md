# HR-Presents ORIVOX

**ORIVOX — Local AI Voice Assistant**

ORIVOX is a local-first voice assistant by **HR-Presents**. Its real runtime pipeline is microphone audio → Faster-Whisper → local conversational model through Ollama → Kokoro speech → speaker playback. Conversation/account data is stored in an application-managed SQLite database.

## Architecture

- `orivox/app.py` — FastAPI application/API and web-client serving
- `orivox/db.py` — SQLite users, conversations, messages and settings
- `orivox/services.py` — lazy-loaded Whisper, local LLM and Kokoro runtime
- `orivox/config.py` — portable environment-aware configuration
- `web/` — responsive light/dark ORIVOX application client
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

Open `http://127.0.0.1:8765` to use ORIVOX.

Models and the database are stored under `%LOCALAPPDATA%\ORIVOX` by default, never under a developer-specific path. Override with `ORIVOX_DATA_DIR`, `ORIVOX_MODEL_DIR`, `ORIVOX_DB_PATH`, `ORIVOX_WHISPER_MODEL`, `ORIVOX_LLM_MODEL`, `ORIVOX_OLLAMA_URL`, or `ORIVOX_PORT`.

## Implemented application workflow

The current build includes real local registration/login, profile updates, persistent settings, dashboard status, dynamic conversation history, text chat, browser microphone capture, live microphone-derived visualization, Whisper transcription, local conversational AI, Kokoro speech synthesis, audio playback, interruption/stop controls, new conversations, conversation reopening/deletion, responsive navigation, notifications, and persistent light/dark/system appearance.

## Privacy

Core speech recognition, conversation generation and speech synthesis are designed to execute locally. ORIVOX does not require cloud transcription for its basic pipeline. Raw microphone recordings are not persisted by the backend in the current implementation.

## Testing

GitHub Actions runs Windows smoke tests for application import/compilation, the web client, registration/login, profile persistence, settings persistence, and empty-audio validation. Full microphone → Whisper → AI → Kokoro → physical speaker validation still requires a real Windows audio device and installed local models.

## Remaining release work

Before ORIVOX is called production-complete, the supplied official ORIVOX logo must be committed as final web/desktop/installer assets, founder/developer links must be verified from the Sentrix product metadata, the desktop application/installer must be packaged, model installation UX must be finalized, and the complete workflow must be exercised on a real Windows machine with microphone and speaker hardware.

Copyright (c) 2026 **HR-Presents**. All rights reserved.
