import mimetypes
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

from .config import OLLAMA_MODEL, VERSION


app = FastAPI(title="HR-Presents ORIVOX", version=VERSION)
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
WEB_DIR = BUNDLE_ROOT / "web"


class Register(BaseModel):
    name: str
    email: str
    password: str


class Login(BaseModel):
    email: str
    password: str


class Chat(BaseModel):
    user_id: int
    conversation_id: int | None = None
    text: str


class ProfileUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    current_password: str | None = None
    new_password: str | None = None


class SettingsUpdate(BaseModel):
    values: dict[str, str | int | float | bool]


class Speech(BaseModel):
    text: str
    voice: str = "af_heart"
    speed: float = 1.0


def _db_symbols():
    from sqlalchemy import delete, select
    from .db import Conversation, Message, SessionLocal, Setting, User, init_db

    init_db()
    return SessionLocal, User, Conversation, Message, Setting, select, delete


def _password_context():
    from passlib.context import CryptContext

    return CryptContext(schemes=["bcrypt"], deprecated="auto")


def _runtime():
    from .services import runtime

    return runtime


def require_user(uid: int):
    SessionLocal, User, _, _, _, _, _ = _db_symbols()
    with SessionLocal() as db:
        user = db.get(User, uid)
        if not user:
            raise HTTPException(401, "Invalid local session")
        return {"id": user.id, "name": user.name, "email": user.email}


def serialize_message(message):
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
    }


def _bundled_file(path: Path, media_type: str | None = None) -> Response:
    # FileResponse/StaticFiles offload file metadata and reads through AnyIO's
    # worker-thread pool. That path can stall inside a frozen, windowed
    # PyInstaller process on Windows. The ORIVOX UI assets are local bundled
    # files, so read them directly and return the bytes from the ASGI thread.
    if not path.is_file():
        raise HTTPException(404, "Asset not found")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise HTTPException(503, f"Bundled client file could not be read: {exc}")
    return Response(
        content=data,
        media_type=media_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream",
    )


@app.get("/")
async def home():
    index = WEB_DIR / "index.html"
    if not index.exists():
        raise HTTPException(503, "ORIVOX web client is not installed")
    return _bundled_file(index, "text/html")


@app.get("/static/{asset_path:path}")
async def static_asset(asset_path: str):
    root = WEB_DIR.resolve()
    target = (WEB_DIR / asset_path).resolve()
    if root not in target.parents or not target.is_file():
        raise HTTPException(404, "Asset not found")
    return _bundled_file(target)


@app.get("/api/status")
async def status():
    runtime = _runtime()
    try:
        import httpx
        from .config import OLLAMA_URL

        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            response.raise_for_status()
        runtime.status["ai"] = "ready"
    except Exception:
        runtime.status["ai"] = "unavailable"
    return {"version": VERSION, "models": runtime.status, "llm": OLLAMA_MODEL}


@app.post("/api/auth/register")
def register(x: Register):
    if not x.name.strip():
        raise HTTPException(400, "Name is required")
    if "@" not in x.email:
        raise HTTPException(400, "Enter a valid email address")
    if len(x.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    SessionLocal, User, _, _, _, select, _ = _db_symbols()
    pwd = _password_context()
    email = x.email.lower().strip()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise HTTPException(409, "Account already exists")
        user = User(name=x.name.strip(), email=email, password_hash=pwd.hash(x.password))
        db.add(user)
        db.commit()
        return {"id": user.id, "name": user.name, "email": user.email}


@app.post("/api/auth/login")
def login(x: Login):
    SessionLocal, User, _, _, _, select, _ = _db_symbols()
    pwd = _password_context()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == x.email.lower().strip()))
        if not user or not pwd.verify(x.password, user.password_hash):
            raise HTTPException(401, "Invalid email or password")
        return {"id": user.id, "name": user.name, "email": user.email}


@app.get("/api/profile/{uid}")
def profile(uid: int):
    return require_user(uid)


@app.put("/api/profile/{uid}")
def update_profile(uid: int, x: ProfileUpdate):
    require_user(uid)
    SessionLocal, User, _, _, _, select, _ = _db_symbols()
    pwd = _password_context()
    with SessionLocal() as db:
        user = db.get(User, uid)
        if x.name is not None and x.name.strip():
            user.name = x.name.strip()
        if x.email is not None:
            email = x.email.lower().strip()
            existing = db.scalar(select(User).where(User.email == email, User.id != uid))
            if existing:
                raise HTTPException(409, "Email already in use")
            user.email = email
        if x.new_password:
            if not x.current_password or not pwd.verify(x.current_password, user.password_hash):
                raise HTTPException(400, "Current password is incorrect")
            if len(x.new_password) < 8:
                raise HTTPException(400, "New password must be at least 8 characters")
            user.password_hash = pwd.hash(x.new_password)
        db.commit()
        return {"id": user.id, "name": user.name, "email": user.email}


@app.get("/api/settings/{uid}")
def get_settings(uid: int):
    require_user(uid)
    SessionLocal, _, _, _, Setting, select, _ = _db_symbols()
    defaults = {
        "theme": "system",
        "voice": "af_heart",
        "speed": "1.0",
        "volume": "1.0",
        "auto_speak": "true",
        "save_audio": "false",
    }
    with SessionLocal() as db:
        rows = db.scalars(select(Setting).where(Setting.user_id == uid)).all()
        defaults.update({row.key: row.value for row in rows})
    return defaults


@app.put("/api/settings/{uid}")
def save_settings(uid: int, x: SettingsUpdate):
    require_user(uid)
    SessionLocal, _, _, _, Setting, select, _ = _db_symbols()
    with SessionLocal() as db:
        for key, value in x.values.items():
            row = db.scalar(select(Setting).where(Setting.user_id == uid, Setting.key == key))
            stored = str(value).lower() if isinstance(value, bool) else str(value)
            if row:
                row.value = stored
            else:
                db.add(Setting(user_id=uid, key=key, value=stored))
        db.commit()
    return get_settings(uid)


@app.get("/api/conversations/{uid}")
def history(uid: int):
    require_user(uid)
    SessionLocal, _, Conversation, Message, _, select, _ = _db_symbols()
    with SessionLocal() as db:
        rows = db.scalars(
            select(Conversation)
            .where(Conversation.user_id == uid)
            .order_by(Conversation.updated_at.desc())
        ).all()
        return [
            {
                "id": row.id,
                "title": row.title,
                "updated_at": row.updated_at,
                "message_count": len(
                    db.scalars(select(Message).where(Message.conversation_id == row.id)).all()
                ),
            }
            for row in rows
        ]


@app.get("/api/conversations/{uid}/{cid}")
def conversation(uid: int, cid: int):
    require_user(uid)
    SessionLocal, _, Conversation, Message, _, select, _ = _db_symbols()
    with SessionLocal() as db:
        conv = db.get(Conversation, cid)
        if not conv or conv.user_id != uid:
            raise HTTPException(404, "Conversation not found")
        messages = db.scalars(
            select(Message).where(Message.conversation_id == cid).order_by(Message.id)
        ).all()
        return {
            "id": conv.id,
            "title": conv.title,
            "messages": [serialize_message(message) for message in messages],
        }


@app.delete("/api/conversations/{uid}/{cid}")
def delete_conversation(uid: int, cid: int):
    require_user(uid)
    SessionLocal, _, Conversation, Message, _, _, delete = _db_symbols()
    with SessionLocal() as db:
        conv = db.get(Conversation, cid)
        if not conv or conv.user_id != uid:
            raise HTTPException(404, "Conversation not found")
        db.execute(delete(Message).where(Message.conversation_id == cid))
        db.delete(conv)
        db.commit()
    return {"ok": True}


@app.post("/api/transcribe")
async def transcribe(request: Request):
    form = await request.form()
    audio = form.get("audio")
    if audio is None or not hasattr(audio, "read"):
        raise HTTPException(400, "Audio recording is required")
    data = await audio.read()
    if not data:
        raise HTTPException(400, "Empty recording")
    try:
        text = await _runtime().transcribe(data)
        if not text:
            raise HTTPException(422, "No speech was detected")
        return {"text": text}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"Speech recognition failed: {exc}")


@app.post("/api/chat")
async def chat(x: Chat):
    require_user(x.user_id)
    if not x.text.strip():
        raise HTTPException(400, "Message is empty")

    SessionLocal, _, Conversation, Message, _, select, _ = _db_symbols()
    with SessionLocal() as db:
        conv = db.get(Conversation, x.conversation_id) if x.conversation_id else None
        if not conv:
            conv = Conversation(user_id=x.user_id, title=x.text.strip()[:72])
            db.add(conv)
            db.flush()
        if conv.user_id != x.user_id:
            raise HTTPException(403, "Conversation unavailable")
        conversation_id = conv.id
        db.add(Message(conversation_id=conversation_id, role="user", content=x.text.strip()))
        db.commit()
        messages = db.scalars(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
        ).all()
        payload = [
            {
                "role": "system",
                "content": "You are ORIVOX, a helpful, concise, private local voice assistant by HR-Presents.",
            }
        ] + [{"role": message.role, "content": message.content} for message in messages]

    try:
        answer = await _runtime().chat(payload)
    except Exception as exc:
        raise HTTPException(503, f"Local AI model unavailable: {exc}")

    from datetime import datetime, timezone

    with SessionLocal() as db:
        conv = db.get(Conversation, conversation_id)
        db.add(Message(conversation_id=conversation_id, role="assistant", content=answer))
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()
    return {"conversation_id": conversation_id, "text": answer}


@app.post("/api/speech")
async def speech(x: Speech):
    if not x.text.strip():
        raise HTTPException(400, "Speech text is empty")
    try:
        audio = await _runtime().speak(x.text, x.voice, x.speed)
        return Response(audio, media_type="audio/wav")
    except Exception as exc:
        raise HTTPException(503, f"Text-to-speech failed: {exc}")
