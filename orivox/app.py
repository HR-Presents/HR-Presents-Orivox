import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from passlib.context import CryptContext
from sqlalchemy import select, delete
from .db import SessionLocal, User, Conversation, Message, Setting
from .services import runtime
from .config import VERSION, OLLAMA_MODEL

app=FastAPI(title="HR-Presents ORIVOX",version=VERSION)
pwd=CryptContext(schemes=["bcrypt"],deprecated="auto")
BUNDLE_ROOT=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent.parent))
WEB_DIR=BUNDLE_ROOT / "web"
if WEB_DIR.exists(): app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

class Register(BaseModel): name:str; email:str; password:str
class Login(BaseModel): email:str; password:str
class Chat(BaseModel): user_id:int; conversation_id:int|None=None; text:str
class ProfileUpdate(BaseModel): name:str|None=None; email:str|None=None; current_password:str|None=None; new_password:str|None=None
class SettingsUpdate(BaseModel): values:dict[str,str|int|float|bool]
class Speech(BaseModel): text:str; voice:str="af_heart"; speed:float=1.0

def require_user(uid:int):
    with SessionLocal() as db:
        u=db.get(User,uid)
        if not u: raise HTTPException(401,"Invalid local session")
        return {"id":u.id,"name":u.name,"email":u.email}

def serialize_message(m): return {"id":m.id,"role":m.role,"content":m.content,"created_at":m.created_at}

@app.get("/")
def home():
    index=WEB_DIR/"index.html"
    if not index.exists(): raise HTTPException(503,"ORIVOX web client is not installed")
    return FileResponse(index)

@app.get("/api/status")
async def status():
    try:
        import httpx
        from .config import OLLAMA_URL
        async with httpx.AsyncClient(timeout=2) as c: (await c.get(f"{OLLAMA_URL}/api/tags")).raise_for_status(); runtime.status["ai"]="ready"
    except Exception: runtime.status["ai"]="unavailable"
    return {"version":VERSION,"models":runtime.status,"llm":OLLAMA_MODEL}

@app.post("/api/auth/register")
def register(x:Register):
    if not x.name.strip(): raise HTTPException(400,"Name is required")
    if "@" not in x.email: raise HTTPException(400,"Enter a valid email address")
    if len(x.password)<8: raise HTTPException(400,"Password must be at least 8 characters")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email==x.email.lower().strip())): raise HTTPException(409,"Account already exists")
        u=User(name=x.name.strip(),email=x.email.lower().strip(),password_hash=pwd.hash(x.password)); db.add(u); db.commit();
        return {"id":u.id,"name":u.name,"email":u.email}

@app.post("/api/auth/login")
def login(x:Login):
    with SessionLocal() as db:
        u=db.scalar(select(User).where(User.email==x.email.lower().strip()))
        if not u or not pwd.verify(x.password,u.password_hash): raise HTTPException(401,"Invalid email or password")
        return {"id":u.id,"name":u.name,"email":u.email}

@app.get("/api/profile/{uid}")
def profile(uid:int): return require_user(uid)

@app.put("/api/profile/{uid}")
def update_profile(uid:int,x:ProfileUpdate):
    require_user(uid)
    with SessionLocal() as db:
        u=db.get(User,uid)
        if x.name is not None and x.name.strip(): u.name=x.name.strip()
        if x.email is not None:
            email=x.email.lower().strip()
            existing=db.scalar(select(User).where(User.email==email,User.id!=uid))
            if existing: raise HTTPException(409,"Email already in use")
            u.email=email
        if x.new_password:
            if not x.current_password or not pwd.verify(x.current_password,u.password_hash): raise HTTPException(400,"Current password is incorrect")
            if len(x.new_password)<8: raise HTTPException(400,"New password must be at least 8 characters")
            u.password_hash=pwd.hash(x.new_password)
        db.commit(); return {"id":u.id,"name":u.name,"email":u.email}

@app.get("/api/settings/{uid}")
def get_settings(uid:int):
    require_user(uid)
    defaults={"theme":"system","voice":"af_heart","speed":"1.0","volume":"1.0","auto_speak":"true","save_audio":"false"}
    with SessionLocal() as db:
        rows=db.scalars(select(Setting).where(Setting.user_id==uid)).all()
        defaults.update({r.key:r.value for r in rows}); return defaults

@app.put("/api/settings/{uid}")
def save_settings(uid:int,x:SettingsUpdate):
    require_user(uid)
    with SessionLocal() as db:
        for k,v in x.values.items():
            row=db.scalar(select(Setting).where(Setting.user_id==uid,Setting.key==k))
            if row: row.value=str(v).lower() if isinstance(v,bool) else str(v)
            else: db.add(Setting(user_id=uid,key=k,value=str(v).lower() if isinstance(v,bool) else str(v)))
        db.commit()
    return get_settings(uid)

@app.get("/api/conversations/{uid}")
def history(uid:int):
    require_user(uid)
    with SessionLocal() as db:
        rows=db.scalars(select(Conversation).where(Conversation.user_id==uid).order_by(Conversation.updated_at.desc())).all()
        return [{"id":r.id,"title":r.title,"updated_at":r.updated_at,"message_count":len(db.scalars(select(Message).where(Message.conversation_id==r.id)).all())} for r in rows]

@app.get("/api/conversations/{uid}/{cid}")
def conversation(uid:int,cid:int):
    require_user(uid)
    with SessionLocal() as db:
        c=db.get(Conversation,cid)
        if not c or c.user_id!=uid: raise HTTPException(404,"Conversation not found")
        msgs=db.scalars(select(Message).where(Message.conversation_id==cid).order_by(Message.id)).all()
        return {"id":c.id,"title":c.title,"messages":[serialize_message(m) for m in msgs]}

@app.delete("/api/conversations/{uid}/{cid}")
def delete_conversation(uid:int,cid:int):
    require_user(uid)
    with SessionLocal() as db:
        c=db.get(Conversation,cid)
        if not c or c.user_id!=uid: raise HTTPException(404,"Conversation not found")
        db.execute(delete(Message).where(Message.conversation_id==cid)); db.delete(c); db.commit(); return {"ok":True}

@app.post("/api/transcribe")
async def transcribe(audio:UploadFile=File(...)):
    data=await audio.read()
    if not data: raise HTTPException(400,"Empty recording")
    try:
        text=await runtime.transcribe(data)
        if not text: raise HTTPException(422,"No speech was detected")
        return {"text":text}
    except HTTPException: raise
    except Exception as e: raise HTTPException(503,f"Speech recognition failed: {e}")

@app.post("/api/chat")
async def chat(x:Chat):
    require_user(x.user_id)
    if not x.text.strip(): raise HTTPException(400,"Message is empty")
    with SessionLocal() as db:
        c=db.get(Conversation,x.conversation_id) if x.conversation_id else None
        if not c:
            c=Conversation(user_id=x.user_id,title=x.text.strip()[:72]); db.add(c); db.flush()
        if c.user_id!=x.user_id: raise HTTPException(403,"Conversation unavailable")
        db.add(Message(conversation_id=c.id,role="user",content=x.text.strip())); db.commit()
        msgs=db.scalars(select(Message).where(Message.conversation_id==c.id).order_by(Message.id)).all()
        payload=[{"role":"system","content":"You are ORIVOX, a helpful, concise, private local voice assistant by HR-Presents."}]+[{"role":m.role,"content":m.content} for m in msgs]
    try: answer=await runtime.chat(payload)
    except Exception as e: raise HTTPException(503,f"Local AI model unavailable: {e}")
    with SessionLocal() as db:
        c=db.get(Conversation,c.id); db.add(Message(conversation_id=c.id,role="assistant",content=answer)); c.updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc); db.commit()
    return {"conversation_id":c.id,"text":answer}

@app.post("/api/speech")
async def speech(x:Speech):
    if not x.text.strip(): raise HTTPException(400,"Speech text is empty")
    try: return Response(await runtime.speak(x.text,x.voice,x.speed),media_type="audio/wav")
    except Exception as e: raise HTTPException(503,f"Text-to-speech failed: {e}")
