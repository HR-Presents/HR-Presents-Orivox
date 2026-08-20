<p align="center">
  <img src="assets/orivox-logo.jpg" alt="HR-Presents ORIVOX" width="420">
</p>

<h1 align="center">ORIVOX</h1>
<p align="center"><strong>Private, local-first AI voice assistant by HR-Presents.</strong></p>

ORIVOX is a Windows local web application. It runs its backend on your computer and opens the product interface in your browser at **http://127.0.0.1:8765** by default.

**Microphone → Faster-Whisper → Local AI (Ollama) → Kokoro → Speaker**

Account data, profiles, settings, conversations and messages remain in local SQLite storage under the user's application data directory.

## Download ORIVOX

### Recommended — ORIVOX v1.0.1 Windows Portable ZIP

The primary customer download is **`ORIVOX-v1.0.1-Windows-Portable.zip`** from the latest GitHub release:

https://github.com/HR-Presents/HR-Presents-Orivox/releases/latest

1. Download `ORIVOX-v1.0.1-Windows-Portable.zip`.
2. Extract the ZIP completely into a new folder.
3. Open the extracted ORIVOX folder.
4. Run `ORIVOX.exe`.
5. ORIVOX starts its local server and opens the browser interface at **http://127.0.0.1:8765**.

No Python or Node.js installation is required for the packaged portable build. Keep the extracted files together because the launcher uses the packaged local server and runtime from the same folder.

An installer may also be published for users who prefer installation, but the **portable ZIP is the recommended ORIVOX distribution**.

## ORIVOX v1.0.1

This release is the redesigned local-web build and includes:

- Premium responsive local web interface
- Top navigation for Overview, Voice Assistant, Conversations, Profile, Settings and Help
- Sentrix-inspired blue, slate and light visual system
- Native UI ORIVOX brand mark and wordmark treatment
- Dynamic local registration and login with hashed passwords
- Persistent local profiles, conversations and settings
- Faster-Whisper speech-to-text, including browser WebM/Opus microphone recordings
- Ollama-backed local conversational AI using `qwen2.5:3b` by default
- Automatic first-time Ollama model provisioning when the configured model is missing
- Live model setup state, model name, download phase, bytes downloaded and percentage in the web interface
- Kokoro local text-to-speech
- Microphone recording, live audio visualization and voice playback controls
- Light, dark and system appearance modes
- SQLite-backed local application data
- Packaged Windows runtime with automated HTTP smoke testing

## First-time local AI setup

ORIVOX uses Ollama for local conversational generation. The default model is **`qwen2.5:3b`**.

If the configured model is not already installed, ORIVOX can provision it through Ollama and exposes the download state to the website so first-time setup does not appear to be a frozen AI response. The interface can display the configured model, current setup phase, downloaded bytes, total bytes and percentage while the model is being pulled.

Ollama runs locally at **http://127.0.0.1:11434** by default. If Ollama itself is not installed/running, install/start Ollama first. Advanced users can manually provision the model with:

```powershell
ollama pull qwen2.5:3b
```

The model is intentionally not embedded inside the ORIVOX ZIP because local AI models are substantially larger than the application package.

## Architecture

- `orivox/app.py` — FastAPI local application and API
- `orivox/db.py` — SQLite users, conversations, messages and settings
- `orivox/services.py` — lazy-loaded Whisper, Ollama and Kokoro services
- `orivox/config.py` — portable environment-aware configuration
- `web/` — responsive ORIVOX browser interface
- `desktop.py` — packaged Windows launcher
- `server.py` — packaged local HTTP server worker
- `ORIVOX.spec` — PyInstaller bundle definition
- `installer/ORIVOX.iss` — optional installer definition
- `run.py` — developer/local browser launcher

The speech recognition, conversational AI and speech synthesis layers are separated so each can be upgraded independently.

## Windows requirements

- Windows 10 or Windows 11 x64
- Working microphone and audio output device for voice features
- Ollama installed/running for local conversational AI
- Internet access during first-time model download if the configured Ollama model is not already present
- Sufficient free disk space for ORIVOX and locally downloaded AI models

The packaged ORIVOX ZIP includes its Python/runtime dependencies. Users do not need to install Python just to launch it.

## Developer setup

Python 3.11 is recommended.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
ollama pull qwen2.5:3b
python run.py
```

Open **http://127.0.0.1:8765** after the server starts.

## Build the Windows portable ZIP

```powershell
.\scripts\build-windows.ps1
```

The **ORIVOX Windows Desktop** GitHub Actions workflow compiles the runtime, runs application tests, smoke-tests the packaged HTTP application, creates the versioned portable ZIP, optionally creates the installer, uploads artifacts and publishes validated `main` builds to GitHub Releases.

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

ORIVOX is designed around a local-first workflow. Speech recognition, conversational generation and voice synthesis are intended to execute on the user's computer. Raw browser microphone recordings are processed for transcription and are not permanently stored by the current API.

## Validation

Automated tests cover startup, authentication, local profile/settings persistence, browser microphone transcription paths, model provisioning/progress state and other application behavior. Windows CI additionally validates the packaged local HTTP runtime before publishing customer packages.

Physical microphone, speaker, Ollama download speed and model performance still depend on the customer's Windows hardware and environment.

## Branding

The official product is **ORIVOX**, created by **HR-Presents**. Repository artwork is stored under `assets/`, while the current web interface renders its compact brand mark and wordmark natively for clean scaling inside the product UI.

Copyright © 2026 **HR-Presents**. All rights reserved.
