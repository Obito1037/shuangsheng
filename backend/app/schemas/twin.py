from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TwinCreateRequest(BaseModel):
    name: str
    subject: str
    goal: str
    stage: str | None = None


class TwinUpdateRequest(BaseModel):
    name: str | None = None
    subject: str | None = None
    goal: str | None = None
    stage: str | None = None


class SourceStats(BaseModel):
    assignments: int = 0
    mistakes: int = 0
    notes: int = 0
    courseware: int = 0
    audio: int = 0
    conversations: int = 0


class TwinConversationSummary(BaseModel):
    title: str
    status: str


class WorkStepRead(BaseModel):
    title: str
    detail: str
    state: str


class LearningOutputRead(BaseModel):
    title: str
    type: str
    detail: str
    status: str


class LearningTwinRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    subject: str
    goal: str
    stage: str
    status: str
    sync_percent: int
    source_stats: SourceStats
    memories: list[str]
    recent_conversations: list[TwinConversationSummary]
    current_work: list[WorkStepRead]
    outputs: list[LearningOutputRead]
    created_at: datetime
    updated_at: datetime


class RouteOptionRead(BaseModel):
    name: str
    strategy: str
    score: int
    duration_minutes: int
    cognitive_load: str
    forgetting_risk: str
    teachers: list[str]
    rationale: str


class StudyPathStepRead(BaseModel):
    index: int
    title: str
    teacher: str
    mode: str
    verification: str


class RouteSimulationResponse(BaseModel):
    twin_id: str
    recommended_route: RouteOptionRead
    routes: list[RouteOptionRead]
    optimal_path: list[StudyPathStepRead]
    evidence: list[str]
    outputs: list[LearningOutputRead]


class TwinSyncResponse(BaseModel):
    twin: LearningTwinRead
    learned_assets: list[str]


class WeakPointRead(BaseModel):
    topic: str
    severity: str
    evidence: str
    next_action: str


class BlackboardRequest(BaseModel):
    topic: str | None = None


class BlackboardStepRead(BaseModel):
    index: int
    title: str
    explanation: str
    formula: str | None = None
    check_question: str | None = None


class BlackboardResponse(BaseModel):
    twin_id: str
    topic: str
    steps: list[BlackboardStepRead]
