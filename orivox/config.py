from pathlib import Path
import os

APP_NAME = "ORIVOX"
VERSION = "1.0.0"
DATA_DIR = Path(os.getenv("ORIVOX_DATA_DIR", Path(os.getenv("LOCALAPPDATA", Path.home())) / "ORIVOX"))
MODEL_DIR = Path(os.getenv("ORIVOX_MODEL_DIR", DATA_DIR / "models"))
DB_PATH = Path(os.getenv("ORIVOX_DB_PATH", DATA_DIR / "orivox.db"))
HOST = os.getenv("ORIVOX_HOST", "127.0.0.1")
PORT = int(os.getenv("ORIVOX_PORT", "8765"))
WHISPER_MODEL = os.getenv("ORIVOX_WHISPER_MODEL", "base.en")
OLLAMA_URL = os.getenv("ORIVOX_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("ORIVOX_LLM_MODEL", "qwen2.5:3b")
KOKORO_VOICE = os.getenv("ORIVOX_KOKORO_VOICE", "af_heart")
for p in (DATA_DIR, MODEL_DIR):
    p.mkdir(parents=True, exist_ok=True)
