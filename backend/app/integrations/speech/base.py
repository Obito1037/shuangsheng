from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpeechTranscriptResult:
    transcript: str
    provider: str
    model: str | None = None


@dataclass(frozen=True, slots=True)
class SpeechSynthesisResult:
    audio: bytes
    content_type: str
    provider: str
    model: str | None = None


class SpeechProvider(ABC):
    @abstractmethod
    def capability_name(self) -> str:
        raise NotImplementedError

    def transcribe_file(self, audio_path: str, **kwargs: object) -> SpeechTranscriptResult:
        raise NotImplementedError("speech_transcription_not_implemented")

    def synthesize(self, text: str, **kwargs: object) -> SpeechSynthesisResult:
        raise NotImplementedError("speech_synthesis_not_implemented")
