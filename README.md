<p align="center">
  <img src="assets/orivox-logo.jpg" alt="HR-Presents ORIVOX" width="420">
</p>

<h1 align="center">ORIVOX</h1>
<p align="center"><strong>Private, local-first AI voice assistant by HR-Presents.</strong></p>

ORIVOX is a Windows local web application. The backend runs on the user's computer and the interface opens in the browser at **http://127.0.0.1:8765**.

**Microphone → Faster-Whisper → Local AI (Ollama / Qwen) → Kokoro → Speaker**

## Download ORIVOX

### Recommended — ORIVOX v1.0.2 Local Web ZIP

The primary customer download is:

**`ORIVOX-v1.0.2-Local-Web.zip`**

Get it from the latest GitHub Release:

https://github.com/HR-Presents/HR-Presents-Orivox/releases/latest

This is intentionally a **local website package**, not a traditional desktop application.

### First launch

1. Download `ORIVOX-v1.0.2-Local-Web.zip`.
2. Extract the ZIP completely into a normal folder.
3. Double-click **`Start ORIVOX.bat`**.
4. A terminal opens and stays visible so setup never looks frozen.
5. ORIVOX checks/install Python 3.11 if necessary.
6. ORIVOX creates a private `.venv` inside the extracted folder.
7. Python requirements install with visible pip progress.
8. ORIVOX checks/install Ollama if necessary.
9. ORIVOX checks the default local model **`qwen2.5:3b`**.
10. If the model is missing, the terminal runs `ollama pull qwen2.5:3b` and shows Ollama's live download percentage, transferred size, total size and speed.
11. When setup finishes, ORIVOX starts locally and opens **http://127.0.0.1:8765** automatically.

Keep the terminal open while using ORIVOX. Press **Ctrl+C** in that terminal to stop the local server.

Later launches reuse the existing `.venv`, installed Python packages, Ollama runtime and Qwen model, so they skip the expensive setup steps and start much faster.

## What v1.0.2 changes

The distribution now behaves the same way users expect from a local web product such as Sentrix:

- no hidden multi-minute AI model setup
- no need to wonder whether Qwen is downloading
- visible first-run terminal setup
- visible Python dependency installation progress
- automatic Ollama detection / installation path
- visible `qwen2.5:3b` pull progress
- browser interface served locally from `127.0.0.1`
- reusable local `.venv` so dependencies are not reinstalled every launch
- local SQLite users, profiles, settings and conversations
- Faster-Whisper speech-to-text
- Kokoro text-to-speech
- live web grounding for questions that require up-to-date information

## Current-data behavior

ORIVOX remains local-first, but questions asking for **latest/current/today/yesterday/live** information can use internet retrieval before the local model writes the response. Examples include recent football results, current news, weather, recent events and other time-sensitive queries.

The LLM still runs through local Ollama. Internet access is required only when downloading dependencies/models or when the user asks for information that must be retrieved from the live web.

## Local AI setup

The default model is:

```text
qwen2.5:3b
```

The first-run launcher checks whether it is already available through Ollama. If it is missing, the launcher runs:

```powershell
ollama pull qwen2.5:3b
```

That command remains visible in the ORIVOX setup terminal so the user can see the actual model download progress rather than sitting on an indefinite "Thinking locally" screen.

## Requirements

- Windows 10 or Windows 11 x64
- Internet connection for first-time setup/model downloads and live-current-data questions
- Microphone and speakers/headphones for voice features
- Enough disk space for Python dependencies and the local Qwen model

Python and Ollama are checked by the launcher. If Python 3.11 or Ollama are missing and Windows Package Manager (`winget`) is available, ORIVOX attempts to install them automatically.

## Local data

Application data is stored under `%LOCALAPPDATA%\ORIVOX` by default.

Supported environment overrides include:

- `ORIVOX_DATA_DIR`
- `ORIVOX_MODEL_DIR`
- `ORIVOX_DB_PATH`
- `ORIVOX_WHISPER_MODEL`
- `ORIVOX_LLM_MODEL`
- `ORIVOX_OLLAMA_URL`
- `ORIVOX_PORT`

## Developer setup

Python 3.11 is recommended:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
ollama pull qwen2.5:3b
python run.py
```

Then open **http://127.0.0.1:8765**.

## Distribution files

- `Start ORIVOX.bat` — customer one-click launcher
- `scripts/bootstrap-local.ps1` — visible first-run setup and local-server bootstrap
- `run.py` — local FastAPI server entry point
- `orivox/` — backend and AI services
- `web/` — browser interface
- `requirements.txt` — local Python dependencies
- `.github/workflows/local-web.yml` — validates and publishes the customer Local Web ZIP

The older compiled Windows desktop bundle can still be maintained separately, but **`ORIVOX-v1.0.2-Local-Web.zip` is now the recommended customer package**.

Copyright © 2026 **HR-Presents**. All rights reserved.
