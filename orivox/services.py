import io
import os
import tempfile
import asyncio
import httpx

from .config import WHISPER_MODEL, MODEL_DIR, OLLAMA_URL, OLLAMA_MODEL, KOKORO_VOICE


class Runtime:
    def __init__(self):
        self.whisper = None
        self.kokoro = None
        self.status = {"whisper": "idle", "kokoro": "idle", "ai": "checking"}

    def load_whisper(self):
        if self.whisper:
            return self.whisper
        self.status["whisper"] = "loading"
        from faster_whisper import WhisperModel

        self.whisper = WhisperModel(
            WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
            download_root=str(MODEL_DIR / "whisper"),
        )
        self.status["whisper"] = "ready"
        return self.whisper

    @staticmethod
    def _audio_suffix(data: bytes) -> str:
        if data.startswith(b"\x1a\x45\xdf\xa3"):
            return ".webm"
        if data.startswith(b"OggS"):
            return ".ogg"
        if data.startswith(b"RIFF"):
            return ".wav"
        if len(data) >= 12 and data[4:8] == b"ftyp":
            return ".m4a"
        return ".audio"

    async def transcribe(self, data: bytes):
        """Transcribe browser-recorded audio with Whisper/PyAV.

        Browser MediaRecorder output is normally WebM/Opus on Chrome/Edge.
        SoundFile/libsndfile cannot reliably decode that container on Windows,
        while faster-whisper's PyAV decoder can.  Write the uploaded bytes to a
        temporary file so Whisper can decode the original browser container.
        """
        if not data:
            raise ValueError("No audio data received")

        model = await asyncio.to_thread(self.load_whisper)
        temp_path = None
        try:
            suffix = self._audio_suffix(data)
            with tempfile.NamedTemporaryFile(prefix="orivox-recording-", suffix=suffix, delete=False) as f:
                f.write(data)
                temp_path = f.name

            segs, _ = await asyncio.to_thread(model.transcribe, temp_path, vad_filter=True)
            return " ".join(s.text.strip() for s in segs).strip()
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    @staticmethod
    def _ollama_error(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get("error"):
                return str(payload["error"])
        except Exception:
            pass
        return response.text.strip() or f"HTTP {response.status_code}"

    async def _pull_ollama_model(self, client: httpx.AsyncClient, model: str) -> None:
        self.status["ai"] = "downloading"
        try:
            response = await client.post(
                f"{OLLAMA_URL}/api/pull",
                json={"name": model, "stream": False},
                timeout=1800,
            )
        except httpx.ConnectError as exc:
            self.status["ai"] = "unavailable"
            raise RuntimeError(
                "The local AI engine is not running. Start Ollama, then reopen ORIVOX."
            ) from exc
        except httpx.TimeoutException as exc:
            self.status["ai"] = "unavailable"
            raise RuntimeError(
                f"Timed out while downloading the local AI model '{model}'. Check your internet connection and try again."
            ) from exc

        if response.is_error:
            self.status["ai"] = "unavailable"
            raise RuntimeError(
                f"Could not download local AI model '{model}': {self._ollama_error(response)}"
            )
        self.status["ai"] = "ready"

    async def chat(self, messages, model=OLLAMA_MODEL):
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                response = await client.post(
                    f"{OLLAMA_URL}/api/chat",
                    json={"model": model, "messages": messages, "stream": False},
                )
            except httpx.ConnectError as exc:
                self.status["ai"] = "unavailable"
                raise RuntimeError(
                    "The local AI engine is not running. Start Ollama, then reopen ORIVOX."
                ) from exc
            except httpx.TimeoutException as exc:
                self.status["ai"] = "unavailable"
                raise RuntimeError("The local AI model took too long to respond.") from exc

            # Ollama returns 404 when the requested model is not installed.
            # Provision the configured local model automatically on first use,
            # then retry the original chat request once.
            if response.status_code == 404:
                error_text = self._ollama_error(response)
                if "model" in error_text.lower() and (
                    "not found" in error_text.lower() or "does not exist" in error_text.lower()
                ):
                    await self._pull_ollama_model(client, model)
                    response = await client.post(
                        f"{OLLAMA_URL}/api/chat",
                        json={"model": model, "messages": messages, "stream": False},
                        timeout=120,
                    )

            if response.is_error:
                self.status["ai"] = "unavailable"
                raise RuntimeError(
                    f"Local AI request failed: {self._ollama_error(response)}"
                )

            payload = response.json()
            content = payload.get("message", {}).get("content", "").strip()
            if not content:
                self.status["ai"] = "unavailable"
                raise RuntimeError("The local AI model returned an empty response.")
            self.status["ai"] = "ready"
            return content

    def load_kokoro(self):
        if self.kokoro:
            return self.kokoro
        self.status["kokoro"] = "loading"
        from kokoro import KPipeline

        self.kokoro = KPipeline(lang_code="a")
        self.status["kokoro"] = "ready"
        return self.kokoro

    async def speak(self, text, voice=KOKORO_VOICE, speed=1.0):
        # Kokoro/Torch and NumPy are intentionally lazy so normal ORIVOX
        # startup remains fast on CPU-only Windows systems.
        import numpy as np
        import soundfile as sf

        pipe = await asyncio.to_thread(self.load_kokoro)
        chunks = []
        for _, _, audio in pipe(text, voice=voice, speed=speed):
            chunks.append(np.asarray(audio, dtype=np.float32))
        if not chunks:
            raise ValueError("No speech generated")
        out = io.BytesIO()
        sf.write(out, np.concatenate(chunks), 24000, format="WAV")
        return out.getvalue()


runtime = Runtime()
