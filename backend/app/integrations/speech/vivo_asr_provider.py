from __future__ import annotations

from app.integrations.speech.base import SpeechProvider


class VivoAsrProvider(SpeechProvider):
    def capability_name(self) -> str:
        return "realtime_short_asr"

