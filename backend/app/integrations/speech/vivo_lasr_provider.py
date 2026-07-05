from __future__ import annotations

from app.integrations.speech.base import SpeechProvider


class VivoLasrProvider(SpeechProvider):
    def capability_name(self) -> str:
        return "long_audio_asr"

