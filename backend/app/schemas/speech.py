from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.twin_brain import MasteryUpdateRead


class SpokenEnglishAnalyzeRequest(BaseModel):
    twin_id: str | None = None
    transcript: str | None = Field(default=None, max_length=8000)
    prompt: str | None = Field(default=None, max_length=1000)


class SpokenEnglishIssueRead(BaseModel):
    text: str
    issue: str
    suggestion: str


class SpokenEnglishResponse(BaseModel):
    status: Literal["pending", "scored"]
    evidence_mode: Literal["pending", "简化模式", "真实画像"]
    transcript: str
    pronunciation: int | None = None
    fluency: int | None = None
    grammar: int | None = None
    vocabulary: int | None = None
    issues: list[SpokenEnglishIssueRead] = []
    correction_plan: list[str] = []
    provider: str
    model: str | None = None
    attempt_id: str | None = None
    mastery_updates: list[MasteryUpdateRead] = []


class SpeechSynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice: str | None = Field(default=None, max_length=80)


class SpeechSynthesisResponse(BaseModel):
    status: Literal["pending", "ready"]
    provider: str
    audio_url: str | None = None
    audio_file_id: str | None = None
    message: str
