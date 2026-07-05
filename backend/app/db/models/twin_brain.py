from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin, utc_now


class KnowledgePoint(IdMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_points"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    twin_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_twins.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False, default="综合学习")
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("knowledge_points.id"), index=True, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="seed")


class KpEdge(IdMixin, TimestampMixin, Base):
    __tablename__ = "kp_edges"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    twin_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_twins.id"), index=True, nullable=False)
    from_kp_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_points.id"), index=True, nullable=False)
    to_kp_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_points.id"), index=True, nullable=False)
    relation: Mapped[str] = mapped_column(String(40), nullable=False, default="related")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)


class ChunkKnowledgePoint(IdMixin, TimestampMixin, Base):
    __tablename__ = "chunk_kp"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    twin_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_twins.id"), index=True, nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_chunks.id"), index=True, nullable=False)
    kp_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_points.id"), index=True, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class Question(IdMixin, TimestampMixin, Base):
    __tablename__ = "questions"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    twin_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_twins.id"), index=True, nullable=False)
    kp_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    solution: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="diagnostic")
    difficulty_elo: Mapped[float] = mapped_column(Float, nullable=False, default=1200.0)
    disc_prior: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class Attempt(IdMixin, Base):
    __tablename__ = "attempts"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    twin_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_twins.id"), index=True, nullable=False)
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("questions.id"), index=True, nullable=False)
    kp_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    is_correct: Mapped[bool] = mapped_column(nullable=False)
    self_rating: Mapped[str | None] = mapped_column(String(20), nullable=True)
    time_spent_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Mistake(IdMixin, TimestampMixin, Base):
    __tablename__ = "mistakes"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    twin_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_twins.id"), index=True, nullable=False)
    question_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("questions.id"), index=True, nullable=True)
    attempt_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("attempts.id"), index=True, nullable=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_image_file_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("files.id"), nullable=True)
    error_type: Mapped[str] = mapped_column(String(60), nullable=False, default="待标注")
    error_analysis: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    variant_question_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class MasteryState(IdMixin, Base):
    __tablename__ = "mastery_states"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    twin_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_twins.id"), index=True, nullable=False)
    kp_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_points.id"), index=True, nullable=False)
    p_mastery: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    ability_elo: Mapped[float] = mapped_column(Float, nullable=False, default=1200.0)
    stability: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    difficulty_fsrs: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class StudyPlan(IdMixin, Base):
    __tablename__ = "study_plans"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    twin_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_twins.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued")
    profile_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    candidates_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    chosen_route_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    narrative: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlanTask(IdMixin, Base):
    __tablename__ = "plan_tasks"

    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("study_plans.id"), index=True, nullable=False)
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    kp_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    question_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    est_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    completion_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class BlackboardLesson(IdMixin, TimestampMixin, Base):
    __tablename__ = "blackboard_lessons"

    twin_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_twins.id"), index=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(240), index=True, nullable=False)
    profile_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False, default="")
    kp_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("knowledge_points.id"), index=True, nullable=True)
    steps_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    model: Mapped[str] = mapped_column(String(120), nullable=False, default="template-fallback")
