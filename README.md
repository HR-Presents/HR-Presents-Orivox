<p align="center">
  <img src="assets/orivox-logo.jpg" alt="HR-Presents ORIVOX" width="720">
</p>

<h1 align="center">HR-Presents ORIVOX</h1>
<p align="center"><strong>Private, local-first AI voice assistant for Windows.</strong></p>

ORIVOX is a locally deployed voice assistant by **HR-Presents**. Its core workflow is:

**Microphone → Faster-Whisper → Local AI → Kokoro → Speaker**

Account data, profile information, settings, conversations and messages are stored locally in SQLite under the user's application data directory.

## Download ORIVOX

### Recommended — Windows Portable ZIP

The primary end-user download is:

**`ORIVOX-Windows-Portable.zip`**

Download it from the latest GitHub release:

**https://github.com/HR-Presents/HR-Presents-Orivox/releases/latest**

Then:

1. Download `ORIVOX-Windows-Portable.zip`.
2. Extract the ZIP completely.
3. Open the extracted ORIVOX folder.
4. Double-click `ORIVOX.exe`.
5. ORIVOX starts locally on the computer. No installer is required.

Keep the extracted files together. `ORIVOX.exe` uses the bundled `ORIVOX-server.exe` and packaged runtime from the same folder.

An optional Windows installer is also published for users who prefer a traditional installation flow, but the **portable ZIP is the main ORIVOX distribution**.

If a release has not been published yet, project maintainers can download the newest validated portable build from the **ORIVOX Windows Desktop** workflow artifacts under GitHub Actions.

## What ORIVOX includes

- Local registration and login with hashed passwords
- Persistent local user profiles
- SQLite conversation and settings storage
- Dynamic dashboard and history data
- Faster-Whisper speech-to-text
- Replaceable local conversational AI service layer
- Ollama-backed default local AI model
- Kokoro text-to-speech
- Microphone recording and live audio visualization
- Voice response playback and interruption controls
- Light, dark and system appearance modes
- Portable Windows desktop runtime
- Separate packaged local server worker for reliable Windows startup

## Architecture

- `orivox/app.py` — FastAPI application and local API
- `orivox/db.py` — SQLite users, conversations, messages and settings
- `orivox/services.py` — lazy-loaded Whisper, local AI and Kokoro runtime
- `orivox/config.py` — portable environment-aware configuration
- `web/` — responsive ORIVOX client
- `desktop.py` — desktop launcher
- `server.py` — packaged local server worker
- `ORIVOX.spec` — PyInstaller desktop bundle definition
- `installer/ORIVOX.iss` — optional Inno Setup installer
- `run.py` — developer/local browser launcher

The STT, conversational AI and TTS layers are separated so each component can be changed or upgraded independently.

## Windows requirements

For the portable application itself:

- Windows 10 or Windows 11 x64
- Working microphone and audio output device
- Enough free disk space for the ORIVOX package and locally downloaded models

The packaged application includes its Python/runtime dependencies. Users do **not** need to install Python just to launch the portable ZIP.

The default conversational model layer uses Ollama with `qwen2.5:3b`. ORIVOX does not currently bundle that model inside the portable ZIP, so the model must be available locally before normal AI conversations can run.

## Local model setup

Install Ollama and pull the default conversational model:

```powershell
ollama pull qwen2.5:3b
```

ORIVOX then connects to the local Ollama service at `http://127.0.0.1:11434` by default.

Faster-Whisper and Kokoro are loaded locally by the ORIVOX runtime. Expensive model components are initialized lazily so the UI can start without loading every AI model at application import time.

## Developer setup

Python 3.11 is recommended for source development.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
ollama pull qwen2.5:3b
python run.py
```

Open `http://127.0.0.1:8765` after the local server starts.

For desktop development:

```powershell
pip install -r requirements-desktop.txt
python desktop.py
```

## Build the Windows portable application

```powershell
.\scripts\build-windows.ps1
```

The GitHub Actions **ORIVOX Windows Desktop** workflow performs automated application tests, builds the packaged Windows runtime, verifies both ORIVOX executables, smoke-tests the packaged HTTP application, creates the portable ZIP and optional installer, and uploads the resulting packages.

On successful builds from `main`, the workflow publishes the validated portable ZIP to the GitHub Releases page so end users have one stable place to download ORIVOX.

## Local data and configuration

ORIVOX stores application-managed data under `%LOCALAPPDATA%\ORIVOX` by default.

Supported environment overrides include:

- `ORIVOX_DATA_DIR`
- `ORIVOX_MODEL_DIR`
- `ORIVOX_DB_PATH`
- `ORIVOX_WHISPER_MODEL`
- `ORIVOX_LLM_MODEL`
- `ORIVOX_OLLAMA_URL`
- `ORIVOX_PORT`

No developer-specific username, drive or absolute development path is required.

## Privacy

ORIVOX is designed around a local-first workflow. Speech recognition, local conversational generation and voice synthesis are intended to execute on the user's computer. Raw microphone recordings are not permanently stored by the current API unless a future explicit storage feature is enabled.

## Validation

Automated tests cover application startup, registration/login, local profile updates, settings persistence, invalid recording handling and packaged runtime health. The Windows workflow additionally verifies the generated desktop executables before creating the downloadable packages.

Physical microphone, speaker and model-performance behavior should still be validated on real Windows hardware before claiming a specific machine configuration is fully supported.

## Branding

The official product name is **ORIVOX** and the parent brand is **HR-Presents**. The repository includes the official ORIVOX artwork under `assets/orivox-logo.jpg` and uses it as the project branding source of truth.

Copyright © 2026 **HR-Presents**. All rights reserved.
