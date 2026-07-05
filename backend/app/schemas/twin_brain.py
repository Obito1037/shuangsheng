from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SelfRating = Literal["again", "hard", "good", "easy"]
MistakeStatus = Literal["open", "reviewing", "resolved"]


class KnowledgePointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    subject: str
    description: str = ""
    source: str
    created_at: datetime


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    twin_id: str
    kp_ids: list[str] = []
    stem: str
    options: list[str] | None = None
    answer: str = ""
    solution: str = ""
    source: str
    difficulty_elo: float
    predicted_correct: float | None = None
    selection_score: float | None = None
    selection_reason: str | None = None
    created_at: datetime


class MasteryPointRead(BaseModel):
    kp_id: str
    name: str
    subject: str
    p_mastery: float
    ability_elo: float
    stability: float
    difficulty_fsrs: float
    attempt_count: int
    correct_count: int
    due_at: datetime | None = None
    status: Literal["new", "weak", "growing", "stable"]


class ErrorDistributionRead(BaseModel):
    error_type: str
    count: int


class MistakeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    twin_id: str
    question_id: str | None = None
    attempt_id: str | None = None
    source_text: str
    error_type: str
    error_analysis: str
    status: str
    variant_question_ids: list[str] = []
    created_at: datetime
    updated_at: datetime


class TwinProfileResponse(BaseModel):
    twin_id: str
    level: int
    xp: int
    sync_percent: int
    evidence_mode: Literal["启动方案", "真实画像"]
    attempts_used: int
    mastery: list[MasteryPointRead]
    weak_points: list[MasteryPointRead]
    error_distribution: list[ErrorDistributionRead]
    recent_mistakes: list[MistakeRead] = []
    next_actions: list[str]


class DiagnoseResponse(BaseModel):
    twin_id: str
    evidence_mode: Literal["启动方案", "真实画像"]
    reason: str
    questions: list[QuestionRead]


class ReviewQueueItemRead(BaseModel):
    id: str
    type: Literal["knowledge_point", "mistake"]
    title: str
    detail: str
    priority: float
    retention: float | None = None
    due_at: datetime | None = None
    kp_id: str | None = None
    mistake_id: str | None = None
    question_id: str | None = None
    action: str


class VariantQuestionsResponse(BaseModel):
    mistake_id: str
    evidence_mode: Literal["简化模式", "真实画像"]
    questions: list[QuestionRead]


class PlanCandidateRead(BaseModel):
    name: str
    strategy: str
    utility: float
    expected_gain: float
    minutes: int
    cognitive_load: float
    forgetting_risk: float
    eliminated: bool
    reason: str


class PlanTaskRead(BaseModel):
    id: str
    index: int
    type: str
    title: str
    detail: str
    kp_ids: list[str] = []
    question_ids: list[str] = []
    est_minutes: int
    completion_criteria: str
    status: str
    outcome: dict = {}


class StudyPlanResponse(BaseModel):
    plan_id: str
    twin_id: str
    status: str
    profile_summary: dict
    candidates: list[PlanCandidateRead]
    chosen_route: dict
    tasks: list[PlanTaskRead]
    narrative: str
    created_at: datetime
    finished_at: datetime | None = None


class PlanTaskUpdateRequest(BaseModel):
    status: Literal["pending", "active", "done", "skipped"] | None = None
    outcome: dict | None = None


class AttemptCreateRequest(BaseModel):
    twin_id: str
    question_id: str | None = None
    stem: str | None = None
    options: list[str] | None = None
    correct_answer: str | None = None
    solution: str | None = None
    kp_ids: list[str] = Field(default_factory=list)
    kp_names: list[str] = Field(default_factory=list)
    is_correct: bool
    self_rating: SelfRating | None = None
    time_spent_sec: int | None = Field(default=None, ge=0)
    error_type: str | None = None
    answer_text: str | None = None


class MasteryUpdateRead(BaseModel):
    kp_id: str
    name: str
    before_p_mastery: float
    after_p_mastery: float
    before_ability_elo: float
    after_ability_elo: float
    expected_correct: float


class AttemptResponse(BaseModel):
    id: str
    twin_id: str
    question: QuestionRead
    is_correct: bool
    self_rating: str | None
    time_spent_sec: int | None
    error_type: str | None
    answer_text: str
    mastery_updates: list[MasteryUpdateRead]
    mistake: MistakeRead | None = None
    created_at: datetime


class MistakeCreateRequest(BaseModel):
    twin_id: str
    question_id: str | None = None
    attempt_id: str | None = None
    source_text: str
    source_image_file_id: str | None = None
    error_type: str | None = None
    error_analysis: str | None = None
    kp_ids: list[str] = Field(default_factory=list)
    kp_names: list[str] = Field(default_factory=list)


class MistakeUpdateRequest(BaseModel):
    status: MistakeStatus | None = None
    error_type: str | None = None
    error_analysis: str | None = None


TwinProfileResponse.model_rebuild()
AttemptResponse.model_rebuild()
