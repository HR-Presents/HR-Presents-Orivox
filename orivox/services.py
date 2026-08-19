import io, asyncio
import numpy as np
import soundfile as sf
import httpx
from .config import WHISPER_MODEL, MODEL_DIR, OLLAMA_URL, OLLAMA_MODEL, KOKORO_VOICE

class Runtime:
    def __init__(self):
        self.whisper=None; self.kokoro=None
        self.status={"whisper":"idle","kokoro":"idle","ai":"checking"}

    def load_whisper(self):
        if self.whisper: return self.whisper
        self.status["whisper"]="loading"
        from faster_whisper import WhisperModel
        self.whisper=WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8", download_root=str(MODEL_DIR/"whisper"))
        self.status["whisper"]="ready"; return self.whisper

    async def transcribe(self, data: bytes):
        model=await asyncio.to_thread(self.load_whisper)
        audio,_=sf.read(io.BytesIO(data), dtype="float32")
        if getattr(audio,"ndim",1)>1: audio=np.mean(audio,axis=1)
        segs,_=await asyncio.to_thread(model.transcribe, audio, vad_filter=True)
        return " ".join(s.text.strip() for s in segs).strip()

    async def chat(self, messages, model=OLLAMA_MODEL):
        async with httpx.AsyncClient(timeout=120) as c:
            r=await c.post(f"{OLLAMA_URL}/api/chat", json={"model":model,"messages":messages,"stream":False})
            r.raise_for_status(); self.status["ai"]="ready"
            return r.json()["message"]["content"]

    def load_kokoro(self):
        if self.kokoro: return self.kokoro
        self.status["kokoro"]="loading"
        from kokoro import KPipeline
        self.kokoro=KPipeline(lang_code="a")
        self.status["kokoro"]="ready"; return self.kokoro

    async def speak(self,text,voice=KOKORO_VOICE,speed=1.0):
        pipe=await asyncio.to_thread(self.load_kokoro)
        chunks=[]
        for _,_,audio in pipe(text, voice=voice, speed=speed): chunks.append(np.asarray(audio,dtype=np.float32))
        if not chunks: raise ValueError("No speech generated")
        out=io.BytesIO(); sf.write(out,np.concatenate(chunks),24000,format="WAV"); return out.getvalue()

runtime=Runtime()
