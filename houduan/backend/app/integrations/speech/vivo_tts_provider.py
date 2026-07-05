from __future__ import annotations

from app.integrations.speech.base import SpeechProvider


class VivoTtsProvider(SpeechProvider):
    def capability_name(self) -> str:
        return "tts_audio_generation"

