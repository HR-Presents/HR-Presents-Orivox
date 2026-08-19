import mimetypes
import sys
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

from .config import OLLAMA_MODEL, VERSION


app = FastAPI(title="HR-Presents ORIVOX", version=VERSION)
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
WEB_DIR = BUNDLE_ROOT / "web"
ASSET_DIR = BUNDLE_ROOT / "assets"


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
    from sqlalchemy import delete, func, select
    from .db import Conversation, Message, SessionLocal, Setting, User, init_db

    init_db()
    return SessionLocal, User, Conversation, Message, Setting, select, delete, func


def _password_context():
    from passlib.context import CryptContext

    return CryptContext(schemes=["bcrypt"], deprecated="auto")


def _runtime():
    from .services import runtime

    return runtime


def require_user(uid: int):
    SessionLocal, User, _, _, _, _, _, _ = _db_symbols()
    with SessionLocal() as db:
        user = db.get(User, uid)
        if not user:
            raise HTTPException(401, "Your local session is no longer valid. Please sign in again.")
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


def _safe_asset(root: Path, asset_path: str) -> Path:
    resolved_root = root.resolve()
    target = (root / asset_path).resolve()
    if resolved_root not in target.parents or not target.is_file():
        raise HTTPException(404, "Asset not found")
    return target


@app.get("/")
async def home():
    index = WEB_DIR / "index.html"
    if not index.exists():
        raise HTTPException(503, "ORIVOX web client is not installed")
    return _bundled_file(index, "text/html")


@app.get("/static/{asset_path:path}")
async def static_asset(asset_path: str):
    return _bundled_file(_safe_asset(WEB_DIR, asset_path))


@app.get("/brand/{asset_path:path}")
async def brand_asset(asset_path: str):
    return _bundled_file(_safe_asset(ASSET_DIR, asset_path))


@app.get("/api/health")
async def health():
    return {"ok": True, "version": VERSION}


@app.get("/api/status")
async def status():
    runtime = _runtime()
    return {"version": VERSION, "models": dict(runtime.status), "llm": OLLAMA_MODEL}


@app.post("/api/auth/register")
def register(x: Register):
    name = x.name.strip()
    email = x.email.lower().strip()
    if not name:
        raise HTTPException(400, "Name is required")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(400, "Enter a valid email address")
    if len(x.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    SessionLocal, User, _, _, _, select, _, _ = _db_symbols()
    pwd = _password_context()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise HTTPException(409, "An account with this email already exists")
        user = User(name=name, email=email, password_hash=pwd.hash(x.password))
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"id": user.id, "name": user.name, "email": user.email}


@app.post("/api/auth/login")
def login(x: Login):
    email = x.email.lower().strip()
    if not email or not x.password:
        raise HTTPException(400, "Email and password are required")
    SessionLocal, User, _, _, _, select, _, _ = _db_symbols()
    pwd = _password_context()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if not user or not pwd.verify(x.password, user.password_hash):
            raise HTTPException(401, "Invalid email or password")
        return {"id": user.id, "name": user.name, "email": user.email}


@app.get("/api/auth/session/{uid}")
def validate_session(uid: int):
    return require_user(uid)


@app.get("/api/profile/{uid}")
def profile(uid: int):
    return require_user(uid)


@app.put("/api/profile/{uid}")
def update_profile(uid: int, x: ProfileUpdate):
    require_user(uid)
    SessionLocal, User, _, _, _, select, _, _ = _db_symbols()
    pwd = _password_context()
    with SessionLocal() as db:
        user = db.get(User, uid)
        if x.name is not None and x.name.strip():
            user.name = x.name.strip()
        if x.email is not None:
            email = x.email.lower().strip()
            if "@" not in email:
                raise HTTPException(400, "Enter a valid email address")
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
        db.refresh(user)
        return {"id": user.id, "name": user.name, "email": user.email}


def _default_settings():
    return {
        "theme": "system",
        "voice": "af_heart",
        "speed": "1.0",
        "volume": "1.0",
        "auto_speak": "true",
        "save_audio": "false",
    }


@app.get("/api/settings/{uid}")
def get_settings(uid: int):
    require_user(uid)
    SessionLocal, _, _, _, Setting, select, _, _ = _db_symbols()
    values = _default_settings()
    with SessionLocal() as db:
        rows = db.scalars(select(Setting).where(Setting.user_id == uid)).all()
        values.update({row.key: row.value for row in rows})
    return values


@app.put("/api/settings/{uid}")
def save_settings(uid: int, x: SettingsUpdate):
    require_user(uid)
    SessionLocal, _, _, _, Setting, select, _, _ = _db_symbols()
    allowed = set(_default_settings())
    with SessionLocal() as db:
        for key, value in x.values.items():
            if key not in allowed:
                continue
            row = db.scalar(select(Setting).where(Setting.user_id == uid, Setting.key == key))
            stored = str(value).lower() if isinstance(value, bool) else str(value)
            if row:
                row.value = stored
            else:
                db.add(Setting(user_id=uid, key=key, value=stored))
        db.commit()
    return get_settings(uid)


@app.get("/api/conversations/{uid}")
def conversations(uid: int):
    require_user(uid)
    SessionLocal, _, Conversation, Message, _, select, _, func = _db_symbols()
    with SessionLocal() as db:
        rows = db.execute(
            select(Conversation, func.count(Message.id).label("message_count"))
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .where(Conversation.user_id == uid)
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc())
        ).all()
        return [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "message_count": int(message_count or 0),
            }
            for conv, message_count in rows
        ]


@app.get("/api/conversations/{uid}/{cid}")
@app.get("/api/conversation/{uid}/{cid}")
def conversation(uid: int, cid: int):
    require_user(uid)
    SessionLocal, _, Conversation, Message, _, select, _, _ = _db_symbols()
    with SessionLocal() as db:
        conv = db.scalar(select(Conversation).where(Conversation.id == cid, Conversation.user_id == uid))
        if not conv:
            raise HTTPException(404, "Conversation not found")
        messages = db.scalars(select(Message).where(Message.conversation_id == cid).order_by(Message.id)).all()
        return {"id": conv.id, "title": conv.title, "messages": [serialize_message(x) for x in messages]}


@app.delete("/api/conversations/{uid}/{cid}")
@app.delete("/api/conversation/{uid}/{cid}")
def delete_conversation(uid: int, cid: int):
    require_user(uid)
    SessionLocal, _, Conversation, Message, _, select, delete, _ = _db_symbols()
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
    text = x.text.strip()
    if not text:
        raise HTTPException(400, "Message cannot be empty")
    SessionLocal, _, Conversation, Message, _, select, _, _ = _db_symbols()
    runtime = _runtime()
    with SessionLocal() as db:
        conv = None
        if x.conversation_id:
            conv = db.scalar(select(Conversation).where(Conversation.id == x.conversation_id, Conversation.user_id == x.user_id))
        if not conv:
            conv = Conversation(user_id=x.user_id, title=text[:60] or "New conversation")
            db.add(conv)
            db.commit()
            db.refresh(conv)
        db.add(Message(conversation_id=conv.id, role="user", content=text))
        conv.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        db.commit()
        history = db.scalars(select(Message).where(Message.conversation_id == conv.id).order_by(Message.id)).all()
        messages = [{"role": m.role, "content": m.content} for m in history]
        conversation_id = conv.id

    try:
        reply = await runtime.chat(messages)
    except Exception as exc:
        raise HTTPException(503, f"AI model unavailable: {exc}")

    with SessionLocal() as db:
        conv = db.get(Conversation, conversation_id)
        db.add(Message(conversation_id=conversation_id, role="assistant", content=reply))
        if conv:
            conv.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        db.commit()
    return {"conversation_id": conversation_id, "response": reply, "text": reply}


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


@app.post("/api/speech")
@app.post("/api/speak")
async def speak(x: Speech):
    if not x.text.strip():
        raise HTTPException(400, "Text is required")
    try:
        audio = await _runtime().speak(x.text.strip(), x.voice, x.speed)
    except Exception as exc:
        raise HTTPException(503, f"Text-to-speech failed: {exc}")
    return Response(content=audio, media_type="audio/wav")
