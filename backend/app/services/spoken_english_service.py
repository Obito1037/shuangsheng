from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SpokenEnglishIssue:
    text: str
    issue: str
    suggestion: str


@dataclass(frozen=True, slots=True)
class SpokenEnglishResult:
    transcript: str
    pronunciation: int | None
    fluency: int | None
    grammar: int | None
    vocabulary: int | None
    issues: list[SpokenEnglishIssue] = field(default_factory=list)
    correction_plan: list[str] = field(default_factory=list)
    provider: str = "pending"


class SpokenEnglishService:
    def analyze(self, *, user_id: str, file_id: str) -> SpokenEnglishResult:
        raise ValueError("spoken_english_pending: configure speech provider before analyzing uploaded voice files")
