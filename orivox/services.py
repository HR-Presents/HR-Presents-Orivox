import io
import os
import json
import re
import tempfile
import asyncio
from datetime import datetime, timezone
import httpx

from .config import WHISPER_MODEL, MODEL_DIR, OLLAMA_URL, OLLAMA_MODEL, KOKORO_VOICE


class Runtime:
    def __init__(self):
        self.whisper = None
        self.kokoro = None
        self.status = {
            "whisper": "idle", "kokoro": "idle", "ai": "checking",
            "ai_model": OLLAMA_MODEL, "ai_download_status": "idle",
            "ai_download_percent": 0, "ai_download_completed": 0, "ai_download_total": 0,
            "web": "ready", "web_last_checked": None,
        }

    def _reset_download(self, model=None):
        self.status.update({"ai_model": model or OLLAMA_MODEL, "ai_download_status": "idle", "ai_download_percent": 0, "ai_download_completed": 0, "ai_download_total": 0})

    def load_whisper(self):
        if self.whisper: return self.whisper
        self.status["whisper"] = "loading"
        from faster_whisper import WhisperModel
        self.whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8", download_root=str(MODEL_DIR / "whisper"))
        self.status["whisper"] = "ready"
        return self.whisper

    @staticmethod
    def _audio_suffix(data: bytes) -> str:
        if data.startswith(b"\x1a\x45\xdf\xa3"): return ".webm"
        if data.startswith(b"OggS"): return ".ogg"
        if data.startswith(b"RIFF"): return ".wav"
        if len(data) >= 12 and data[4:8] == b"ftyp": return ".m4a"
        return ".audio"

    async def transcribe(self, data: bytes):
        if not data: raise ValueError("No audio data received")
        model = await asyncio.to_thread(self.load_whisper)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="orivox-recording-", suffix=self._audio_suffix(data), delete=False) as f:
                f.write(data); temp_path = f.name
            segs, _ = await asyncio.to_thread(model.transcribe, temp_path, vad_filter=True)
            return " ".join(s.text.strip() for s in segs).strip()
        finally:
            if temp_path:
                try: os.unlink(temp_path)
                except OSError: pass

    @staticmethod
    def needs_web_search(text: str) -> bool:
        q = text.lower().strip()
        current = r"\b(latest|today|tonight|yesterday|tomorrow|current|currently|now|recent|breaking|live|this week|this month|up[- ]?to[- ]?date|real[- ]?time|score|scores|result|results|weather|forecast|price|prices|stock|market|news|election|president|prime minister|ceo|release|version|update|updates)\b"
        dateish = r"\b(20\d{2}|monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|march|april|may|june|july|august|september|october|november|december)\b"
        return bool(re.search(current, q) or re.search(dateish, q))

    @staticmethod
    def _search_sync(query: str, max_results: int = 6):
        from ddgs import DDGS
        rows = DDGS().text(query, max_results=max_results)
        clean = []
        for row in rows or []:
            url = str(row.get("href") or row.get("url") or "").strip()
            title = str(row.get("title") or "Untitled").strip()
            body = str(row.get("body") or row.get("content") or "").strip()
            if url and url.startswith(("http://", "https://")):
                clean.append({"title": title[:180], "url": url, "snippet": body[:700]})
        return clean[:max_results]

    async def web_search(self, query: str):
        self.status["web"] = "searching"
        try:
            results = await asyncio.wait_for(asyncio.to_thread(self._search_sync, query), timeout=18)
        except Exception as exc:
            self.status["web"] = "unavailable"
            raise RuntimeError(f"Live web search failed: {exc}") from exc
        self.status["web"] = "ready"
        self.status["web_last_checked"] = datetime.now(timezone.utc).isoformat()
        if not results:
            raise RuntimeError("Live web search returned no verifiable results")
        return results

    @staticmethod
    def _web_context(query: str, results: list[dict]) -> str:
        checked = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            "LIVE WEB CONTEXT", f"Search query: {query}", f"Retrieved: {checked}",
            "Use these live results for current facts. Do not claim your training cutoff prevents answering.",
            "Do not invent facts missing from the results. If sources conflict, say so. Cite sources as [1], [2], etc.",
        ]
        for i, item in enumerate(results, 1):
            lines += [f"[{i}] {item['title']}", f"URL: {item['url']}", f"Snippet: {item['snippet']}"]
        return "\n".join(lines)

    @staticmethod
    def _ollama_error(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get("error"): return str(payload["error"])
        except Exception: pass
        return response.text.strip() or f"HTTP {response.status_code}"

    def _apply_pull_event(self, payload: dict, model: str) -> None:
        completed, total = int(payload.get("completed") or 0), int(payload.get("total") or 0)
        percent = round((completed / total) * 100, 1) if total else self.status.get("ai_download_percent", 0)
        self.status.update({"ai": "downloading", "ai_model": model, "ai_download_status": str(payload.get("status") or "Downloading model"), "ai_download_percent": min(100, percent), "ai_download_completed": completed, "ai_download_total": total})

    async def _pull_ollama_model(self, client: httpx.AsyncClient, model: str) -> None:
        self.status.update({"ai": "downloading", "ai_model": model, "ai_download_status": "Starting download"})
        try:
            async with client.stream("POST", f"{OLLAMA_URL}/api/pull", json={"name": model, "stream": True}, timeout=1800) as response:
                if response.is_error:
                    body = await response.aread(); self.status["ai"] = "unavailable"
                    raise RuntimeError(f"Could not download local AI model '{model}': {body.decode(errors='ignore').strip() or f'HTTP {response.status_code}'}")
                async for line in response.aiter_lines():
                    if not line: continue
                    try: payload = json.loads(line)
                    except json.JSONDecodeError: continue
                    if payload.get("error"):
                        self.status["ai"] = "unavailable"; raise RuntimeError(f"Could not download local AI model '{model}': {payload['error']}")
                    self._apply_pull_event(payload, model)
        except httpx.ConnectError as exc:
            self.status["ai"] = "unavailable"; raise RuntimeError("The local AI engine is not running. Start Ollama, then reopen ORIVOX.") from exc
        except httpx.TimeoutException as exc:
            self.status["ai"] = "unavailable"; raise RuntimeError(f"Timed out while downloading the local AI model '{model}'. Check your internet connection and try again.") from exc
        self.status.update({"ai": "ready", "ai_model": model, "ai_download_status": "Model ready", "ai_download_percent": 100})

    async def chat(self, messages, model=OLLAMA_MODEL):
        self.status["ai_model"] = model
        source_results = []
        prompt_messages = list(messages)
        user_text = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        if self.needs_web_search(user_text):
            try:
                source_results = await self.web_search(user_text)
                prompt_messages = [{"role": "system", "content": self._web_context(user_text, source_results)}] + prompt_messages
            except RuntimeError as exc:
                prompt_messages = [{"role": "system", "content": f"The user asked for current information, but live web retrieval failed ({exc}). Clearly say current facts could not be verified. Do not substitute stale training knowledge or fabricate current data."}] + prompt_messages

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                response = await client.post(f"{OLLAMA_URL}/api/chat", json={"model": model, "messages": prompt_messages, "stream": False})
            except httpx.ConnectError as exc:
                self.status["ai"] = "unavailable"; raise RuntimeError("The local AI engine is not running. Start Ollama, then reopen ORIVOX.") from exc
            except httpx.TimeoutException as exc:
                self.status["ai"] = "unavailable"; raise RuntimeError("The local AI model took too long to respond.") from exc
            if response.status_code == 404:
                error_text = self._ollama_error(response)
                if "model" in error_text.lower() and ("not found" in error_text.lower() or "does not exist" in error_text.lower()):
                    await self._pull_ollama_model(client, model)
                    response = await client.post(f"{OLLAMA_URL}/api/chat", json={"model": model, "messages": prompt_messages, "stream": False}, timeout=120)
            if response.is_error:
                self.status["ai"] = "unavailable"; raise RuntimeError(f"Local AI request failed: {self._ollama_error(response)}")
            payload = response.json(); content = payload.get("message", {}).get("content", "").strip()
            if not content:
                self.status["ai"] = "unavailable"; raise RuntimeError("The local AI model returned an empty response.")
            self.status["ai"] = "ready"; self.status["ai_download_status"] = "Model ready"
            if source_results:
                cited = "\n\nSources:\n" + "\n".join(f"[{i}] {r['title']} — {r['url']}" for i, r in enumerate(source_results, 1))
                content += cited
            return content

    def load_kokoro(self):
        if self.kokoro: return self.kokoro
        self.status["kokoro"] = "loading"
        from kokoro import KPipeline
        self.kokoro = KPipeline(lang_code="a")
        self.status["kokoro"] = "ready"
        return self.kokoro

    async def speak(self, text, voice=KOKORO_VOICE, speed=1.0):
        import numpy as np
        import soundfile as sf
        pipe = await asyncio.to_thread(self.load_kokoro)
        chunks = [np.asarray(audio, dtype=np.float32) for _, _, audio in pipe(text, voice=voice, speed=speed)]
        if not chunks: raise ValueError("No speech generated")
        out = io.BytesIO(); sf.write(out, np.concatenate(chunks), 24000, format="WAV")
        return out.getvalue()


runtime = Runtime()
