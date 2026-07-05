from __future__ import annotations

import json
import time
import uuid
import wave
from pathlib import Path
from urllib.parse import urlencode

from app.core.config import VivoSettings, load_settings
from app.core.errors import ProviderErrorType, provider_error
from app.integrations.speech.base import SpeechProvider, SpeechTranscriptResult

try:
    import websocket
except ImportError:  # pragma: no cover - exercised when optional dependency is absent
    websocket = None


class VivoAsrProvider(SpeechProvider):
    provider = "vivo"
    capability = "realtime_short_asr"

    def __init__(self, *, settings: VivoSettings | None = None) -> None:
        self.settings = settings or load_settings()

    def capability_name(self) -> str:
        return self.capability

    def transcribe_file(self, audio_path: str, **kwargs: object) -> SpeechTranscriptResult:
        request_id = uuid.uuid4().hex
        self.settings.require_credentials(self.capability)
        if websocket is None:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.MISSING_CONFIG,
                "websocket-client is required for realtime ASR.",
                request_id=request_id,
            )
        pcm = self._load_pcm_16k_mono(audio_path, request_id=request_id)
        url = self._build_ws_url(request_id=request_id, user_id=str(kwargs.get("user_id") or request_id))
        headers = [f"Authorization: Bearer {self.settings.vivo_app_key}"]
        texts: list[str] = []
        try:
            ws = websocket.create_connection(url, header=headers, timeout=self.settings.http_timeout_seconds)
            ws.send(
                json.dumps(
                    {
                        "type": "started",
                        "request_id": request_id,
                        "asr_info": {
                            "end_vad_time": int(kwargs.get("end_vad_time") or 1500),
                            "audio_type": "pcm",
                            "chinese2digital": int(kwargs.get("chinese2digital") or 1),
                            "punctuation": int(kwargs.get("punctuation") or 1),
                        },
                        "business_info": str(kwargs.get("business_info") or ""),
                    },
                    ensure_ascii=False,
                )
            )
            self._drain_started(ws, request_id=request_id)
            frame_size = 1280
            for index in range(0, len(pcm), frame_size):
                ws.send_binary(pcm[index : index + frame_size])
                time.sleep(0.01)
            ws.send_binary(b"--end--")
            deadline = time.time() + self.settings.http_timeout_seconds
            while time.time() < deadline:
                raw = ws.recv()
                data = json.loads(raw) if isinstance(raw, str) else {}
                if data.get("action") == "error" or data.get("code") not in (0, None):
                    raise provider_error(
                        self.provider,
                        self.capability,
                        ProviderErrorType.UNKNOWN_ERROR,
                        "ASR provider returned an error.",
                        request_id=request_id,
                        raw_error=data,
                    )
                if data.get("action") == "result":
                    text = ((data.get("data") or {}).get("text") or "").strip()
                    if text:
                        texts.append(text)
                    if data.get("is_finish") or (data.get("data") or {}).get("is_last"):
                        break
            try:
                ws.send_binary(b"--close--")
                ws.close()
            except Exception:
                pass
        except Exception as exc:
            if hasattr(exc, "error_type"):
                raise
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.PROVIDER_UNAVAILABLE,
                "ASR provider call failed.",
                request_id=request_id,
                raw_error=str(exc),
            ) from exc
        transcript = "".join(texts).strip()
        if not transcript:
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.PARSE_FAILED,
                "ASR returned no transcript.",
                request_id=request_id,
            )
        return SpeechTranscriptResult(transcript=transcript, provider=self.provider, model="shortasrinput")

    def _build_ws_url(self, *, request_id: str, user_id: str) -> str:
        safe_user_id = "".join(ch for ch in user_id.lower() if ch.isalnum())[:32].ljust(32, "0")
        query = urlencode(
            {
                "client_version": "unknown",
                "package": "unknown",
                "sdk_version": "unknown",
                "user_id": safe_user_id,
                "android_version": "unknown",
                "system_time": str(int(time.time() * 1000)),
                "net_type": "1",
                "engineid": "shortasrinput",
                "requestId": request_id,
            }
        )
        return f"ws://api-ai.vivo.com.cn/asr/v2?{query}"

    def _drain_started(self, ws: websocket.WebSocket, *, request_id: str) -> None:
        raw = ws.recv()
        data = json.loads(raw) if isinstance(raw, str) else {}
        if data.get("action") == "error" or data.get("code") not in (0, None):
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.UNKNOWN_ERROR,
                "ASR handshake failed.",
                request_id=request_id,
                raw_error=data,
            )

    def _load_pcm_16k_mono(self, audio_path: str, *, request_id: str) -> bytes:
        path = Path(audio_path)
        if not path.exists():
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.INVALID_REQUEST,
                "Audio file does not exist.",
                request_id=request_id,
                raw_error=audio_path,
            )
        if path.suffix.lower() != ".wav":
            raise provider_error(
                self.provider,
                self.capability,
                ProviderErrorType.UNSUPPORTED_FORMAT,
                "Realtime ASR currently supports 16k/16bit/mono wav input in local backend.",
                request_id=request_id,
                raw_error=path.suffix,
            )
        with wave.open(str(path), "rb") as reader:
            channels = reader.getnchannels()
            sample_width = reader.getsampwidth()
            sample_rate = reader.getframerate()
            if channels != 1 or sample_width != 2 or sample_rate != 16000:
                raise provider_error(
                    self.provider,
                    self.capability,
                    ProviderErrorType.UNSUPPORTED_FORMAT,
                    "Realtime ASR requires 16kHz, 16-bit, mono PCM wav.",
                    request_id=request_id,
                    raw_error={"channels": channels, "sample_width": sample_width, "sample_rate": sample_rate},
                )
            raw = reader.readframes(reader.getnframes())
        return raw
