# HR-Presents ORIVOX

**ORIVOX — Local AI Voice Assistant**

ORIVOX is a local-first voice assistant by **HR-Presents**. Its runtime pipeline is microphone audio → Faster-Whisper → local conversational model through Ollama → Kokoro speech → speaker playback. Conversation and account data is stored in an application-managed SQLite database.

## Architecture

- `orivox/app.py` — FastAPI application/API and local web client serving
- `orivox/db.py` — SQLite users, conversations, messages and settings
- `orivox/services.py` — lazy-loaded Whisper, local LLM and Kokoro runtime
- `orivox/config.py` — portable environment-aware configuration
- `web/` — responsive ORIVOX client
- `desktop.py` — native PyWebView desktop launcher
- `ORIVOX.spec` — PyInstaller desktop bundle definition
- `installer/ORIVOX.iss` — Inno Setup installer definition
- `run.py` — browser/local server launcher

The code separates speech recognition, conversational AI and speech synthesis so each model layer can be upgraded independently.

## Windows local setup

Requirements: Windows 10/11 x64, Python 3.11 recommended, working microphone/speaker, and Ollama for the default local conversational model.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
ollama pull qwen2.5:3b
python run.py
```

Open `http://127.0.0.1:8765` after the server starts.

## Desktop development

```powershell
pip install -r requirements-desktop.txt
python desktop.py
```

The desktop shell starts the same local FastAPI application in-process and displays it in a native application window. Closing the ORIVOX window requests a clean server shutdown.

## Build the Windows application

From PowerShell:

```powershell
.\scripts\build-windows.ps1
```

This builds a one-directory `ORIVOX.exe` package and creates `dist\ORIVOX-Windows-Portable.zip`. The GitHub Actions `ORIVOX Windows Desktop` workflow additionally compiles `ORIVOX-Setup-1.0.0.exe` with Inno Setup and uploads both packages as workflow artifacts.

The installer does **not** bundle a conversational model. Install Ollama and run:

```powershell
ollama pull qwen2.5:3b
```

before the first AI conversation, or configure another supported local model through the ORIVOX environment settings.

## Configuration and data

Models and the database are stored under `%LOCALAPPDATA%\ORIVOX` by default, never under a developer-specific path. Supported overrides include `ORIVOX_DATA_DIR`, `ORIVOX_MODEL_DIR`, `ORIVOX_DB_PATH`, `ORIVOX_WHISPER_MODEL`, `ORIVOX_LLM_MODEL`, `ORIVOX_OLLAMA_URL`, and `ORIVOX_PORT`.

## Privacy

Core speech recognition, conversation generation and voice synthesis are designed to execute locally. ORIVOX does not require cloud transcription for its basic pipeline. Raw microphone recordings are not persisted by the current API.

## Validation status

Automated Windows tests cover application loading, registration/login, profile persistence, settings persistence and invalid recording handling. The Windows packaging workflow builds the desktop bundle and installer on GitHub-hosted Windows runners.

A release must **not** be described as fully hardware-validated until the packaged build is also exercised on a real Windows computer with an actual microphone and speaker through the complete microphone → Whisper → AI → Kokoro → playback flow.

## Branding

The product name is **ORIVOX** and the parent brand is **HR-Presents**. Official web, favicon and installer assets must use the supplied ORIVOX artwork without redesigning or recoloring it.

Copyright (c) 2026 **HR-Presents**. All rights reserved.
