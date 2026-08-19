from fastapi import FastAPI, HTTPException, UploadFile, File, Response
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from sqlalchemy import select
from .db import SessionLocal, User, Conversation, Message
from .services import runtime
from .config import VERSION, OLLAMA_MODEL

app=FastAPI(title="HR-Presents ORIVOX",version=VERSION)
pwd=CryptContext(schemes=["bcrypt"],deprecated="auto")
class Register(BaseModel): name:str; email:str; password:str
class Login(BaseModel): email:str; password:str
class Chat(BaseModel): user_id:int; conversation_id:int|None=None; text:str

def user(uid):
    with SessionLocal() as db:
        u=db.get(User,uid)
        if not u: raise HTTPException(401,"Invalid session")
        return u

@app.get("/api/status")
async def status():
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2) as c: (await c.get("http://127.0.0.1:11434/api/tags")).raise_for_status(); runtime.status["ai"]="ready"
    except Exception: runtime.status["ai"]="unavailable"
    return {"version":VERSION,"models":runtime.status,"llm":OLLAMA_MODEL}

@app.post("/api/auth/register")
def register(x:Register):
    if len(x.password)<8: raise HTTPException(400,"Password must be at least 8 characters")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email==x.email.lower())): raise HTTPException(409,"Account already exists")
        u=User(name=x.name.strip(),email=x.email.lower(),password_hash=pwd.hash(x.password)); db.add(u); db.commit(); return {"id":u.id,"name":u.name,"email":u.email}

@app.post("/api/auth/login")
def login(x:Login):
    with SessionLocal() as db:
        u=db.scalar(select(User).where(User.email==x.email.lower()))
        if not u or not pwd.verify(x.password,u.password_hash): raise HTTPException(401,"Invalid login")
        return {"id":u.id,"name":u.name,"email":u.email}

@app.get("/api/conversations/{uid}")
def history(uid:int):
    user(uid)
    with SessionLocal() as db:
        rows=db.scalars(select(Conversation).where(Conversation.user_id==uid).order_by(Conversation.updated_at.desc())).all()
        return [{"id":r.id,"title":r.title,"updated_at":r.updated_at} for r in rows]

@app.post("/api/transcribe")
async def transcribe(audio:UploadFile=File(...)):
    data=await audio.read()
    if not data: raise HTTPException(400,"Empty recording")
    try: return {"text":await runtime.transcribe(data)}
    except Exception as e: raise HTTPException(503,f"Speech recognition failed: {e}")

@app.post("/api/chat")
async def chat(x:Chat):
    user(x.user_id)
    if not x.text.strip(): raise HTTPException(400,"Message is empty")
    with SessionLocal() as db:
        c=db.get(Conversation,x.conversation_id) if x.conversation_id else None
        if not c:
            c=Conversation(user_id=x.user_id,title=x.text.strip()[:72]); db.add(c); db.flush()
        if c.user_id!=x.user_id: raise HTTPException(403,"Conversation unavailable")
        db.add(Message(conversation_id=c.id,role="user",content=x.text.strip())); db.commit()
        msgs=db.scalars(select(Message).where(Message.conversation_id==c.id).order_by(Message.id)).all()
        payload=[{"role":"system","content":"You are ORIVOX, a helpful private local voice assistant by HR-Presents."}]+[{"role":m.role,"content":m.content} for m in msgs]
    try: answer=await runtime.chat(payload)
    except Exception as e: raise HTTPException(503,f"Local AI model unavailable: {e}")
    with SessionLocal() as db: db.add(Message(conversation_id=c.id,role="assistant",content=answer)); db.commit()
    return {"conversation_id":c.id,"text":answer}

class Speech(BaseModel): text:str; voice:str="af_heart"; speed:float=1.0
@app.post("/api/speech")
async def speech(x:Speech):
    try: return Response(await runtime.speak(x.text,x.voice,x.speed),media_type="audio/wav")
    except Exception as e: raise HTTPException(503,f"Text-to-speech failed: {e}")
