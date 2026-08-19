import mimetypes
import sys
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
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


@app.get("/api/health")
async def health():
    return {"ok": True, "version": VERSION}


@app.get("/api/status")
async def status():
    runtime = _runtime()
    return {"version": VERSION, "models": dict(runtime.status), "llm": OLLAMA_MODEL}


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
            if row:
                row.value = str(value)
            else:
                db.add(Setting(user_id=uid, key=key, value=str(value)))
        db.commit()
    return {"ok": True}


@app.get("/api/conversations/{uid}")
def conversations(uid: int):
    require_user(uid)
    SessionLocal, _, Conversation, _, _, select, _ = _db_symbols()
    with SessionLocal() as db:
        rows = db.scalars(select(Conversation).where(Conversation.user_id == uid).order_by(Conversation.updated_at.desc())).all()
        return [{"id": x.id, "title": x.title, "created_at": x.created_at, "updated_at": x.updated_at} for x in rows]


@app.get("/api/conversation/{uid}/{cid}")
def conversation(uid: int, cid: int):
    require_user(uid)
    SessionLocal, _, Conversation, Message, _, select, _ = _db_symbols()
    with SessionLocal() as db:
        conv = db.scalar(select(Conversation).where(Conversation.id == cid, Conversation.user_id == uid))
        if not conv:
            raise HTTPException(404, "Conversation not found")
        messages = db.scalars(select(Message).where(Message.conversation_id == cid).order_by(Message.id)).all()
        return {"id": conv.id, "title": conv.title, "messages": [serialize_message(x) for x in messages]}


@app.delete("/api/conversation/{uid}/{cid}")
def delete_conversation(uid: int, cid: int):
    require_user(uid)
    SessionLocal, _, Conversation, Message, _, select, delete = _db_symbols()
    with SessionLocal() as db:
        conv = db.scalar(select(Conversation).where(Conversation.id == cid, Conversation.user_id == uid))
        if not conv:
            raise HTTPException(404, "Conversation not found")
        db.execute(delete(Message).where(Message.conversation_id == cid))
        db.delete(conv)
        db.commit()
    return {"ok": True}


@app.post("/api/chat")
async def chat(x: Chat):
    require_user(x.user_id)
    SessionLocal, _, Conversation, Message, _, select, _ = _db_symbols()
    runtime = _runtime()
    with SessionLocal() as db:
        conv = None
        if x.conversation_id:
            conv = db.scalar(select(Conversation).where(Conversation.id == x.conversation_id, Conversation.user_id == x.user_id))
        if not conv:
            conv = Conversation(user_id=x.user_id, title=(x.text.strip()[:60] or "New conversation"))
            db.add(conv)
            db.commit()
            db.refresh(conv)
        db.add(Message(conversation_id=conv.id, role="user", content=x.text.strip()))
        db.commit()
        history = db.scalars(select(Message).where(Message.conversation_id == conv.id).order_by(Message.id)).all()
        messages = [{"role": m.role, "content": m.content} for m in history]

    try:
        reply = await runtime.chat(messages)
    except Exception as exc:
        raise HTTPException(503, f"AI model unavailable: {exc}")

    with SessionLocal() as db:
        db.add(Message(conversation_id=conv.id, role="assistant", content=reply))
        db.commit()
    return {"conversation_id": conv.id, "response": reply}


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    data = await audio.read()
    if not data:
        raise HTTPException(400, "No audio received")
    try:
        text = await _runtime().transcribe(data)
    except Exception as exc:
        raise HTTPException(503, f"Speech recognition failed: {exc}")
    if not text:
        raise HTTPException(422, "No speech detected")
    return {"text": text}


@app.post("/api/speak")
async def speak(x: Speech):
    if not x.text.strip():
        raise HTTPException(400, "Text is required")
    try:
        audio = await _runtime().speak(x.text.strip(), x.voice, x.speed)
    except Exception as exc:
        raise HTTPException(503, f"Text-to-speech failed: {exc}")
    return Response(content=audio, media_type="audio/wav")
