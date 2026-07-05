"""M1 twin brain data model.

Revision ID: 20260705_0001
Revises:
Create Date: 2026-07-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260705_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("learning_twins", sa.Column("level", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("learning_twins", sa.Column("xp", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("learning_twins", sa.Column("profile_json", sa.Text(), nullable=False, server_default="{}"))
    op.add_column("learning_records", sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"))

    op.create_table(
        "knowledge_points",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("twin_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("subject", sa.String(length=120), nullable=False, server_default="综合学习"),
        sa.Column("parent_id", sa.String(length=36), nullable=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="seed"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["knowledge_points.id"]),
        sa.ForeignKeyConstraint(["twin_id"], ["learning_twins.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_points_user_id", "knowledge_points", ["user_id"])
    op.create_index("ix_knowledge_points_twin_id", "knowledge_points", ["twin_id"])
    op.create_index("ix_knowledge_points_name", "knowledge_points", ["name"])
    op.create_index("ix_knowledge_points_parent_id", "knowledge_points", ["parent_id"])

    op.create_table(
        "kp_edges",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("twin_id", sa.String(length=36), nullable=False),
        sa.Column("from_kp_id", sa.String(length=36), nullable=False),
        sa.Column("to_kp_id", sa.String(length=36), nullable=False),
        sa.Column("relation", sa.String(length=40), nullable=False, server_default="related"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["from_kp_id"], ["knowledge_points.id"]),
        sa.ForeignKeyConstraint(["to_kp_id"], ["knowledge_points.id"]),
        sa.ForeignKeyConstraint(["twin_id"], ["learning_twins.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kp_edges_user_id", "kp_edges", ["user_id"])
    op.create_index("ix_kp_edges_twin_id", "kp_edges", ["twin_id"])
    op.create_index("ix_kp_edges_from_kp_id", "kp_edges", ["from_kp_id"])
    op.create_index("ix_kp_edges_to_kp_id", "kp_edges", ["to_kp_id"])

    op.create_table(
        "chunk_kp",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("twin_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("kp_id", sa.String(length=36), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"]),
        sa.ForeignKeyConstraint(["kp_id"], ["knowledge_points.id"]),
        sa.ForeignKeyConstraint(["twin_id"], ["learning_twins.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chunk_kp_user_id", "chunk_kp", ["user_id"])
    op.create_index("ix_chunk_kp_twin_id", "chunk_kp", ["twin_id"])
    op.create_index("ix_chunk_kp_chunk_id", "chunk_kp", ["chunk_id"])
    op.create_index("ix_chunk_kp_kp_id", "chunk_kp", ["kp_id"])

    op.create_table(
        "questions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("twin_id", sa.String(length=36), nullable=False),
        sa.Column("kp_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("stem", sa.Text(), nullable=False),
        sa.Column("options_json", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=False, server_default=""),
        sa.Column("solution", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="diagnostic"),
        sa.Column("difficulty_elo", sa.Float(), nullable=False, server_default="1200.0"),
        sa.Column("disc_prior", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("embedding_json", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["twin_id"], ["learning_twins.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_questions_user_id", "questions", ["user_id"])
    op.create_index("ix_questions_twin_id", "questions", ["twin_id"])

    op.create_table(
        "attempts",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("twin_id", sa.String(length=36), nullable=False),
        sa.Column("question_id", sa.String(length=36), nullable=False),
        sa.Column("kp_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("self_rating", sa.String(length=20), nullable=True),
        sa.Column("time_spent_sec", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(length=60), nullable=True),
        sa.Column("answer_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.ForeignKeyConstraint(["twin_id"], ["learning_twins.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attempts_user_id", "attempts", ["user_id"])
    op.create_index("ix_attempts_twin_id", "attempts", ["twin_id"])
    op.create_index("ix_attempts_question_id", "attempts", ["question_id"])

    op.create_table(
        "mistakes",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("twin_id", sa.String(length=36), nullable=False),
        sa.Column("question_id", sa.String(length=36), nullable=True),
        sa.Column("attempt_id", sa.String(length=36), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_image_file_id", sa.String(length=36), nullable=True),
        sa.Column("error_type", sa.String(length=60), nullable=False, server_default="待标注"),
        sa.Column("error_analysis", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("variant_question_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["attempts.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.ForeignKeyConstraint(["source_image_file_id"], ["files.id"]),
        sa.ForeignKeyConstraint(["twin_id"], ["learning_twins.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mistakes_user_id", "mistakes", ["user_id"])
    op.create_index("ix_mistakes_twin_id", "mistakes", ["twin_id"])
    op.create_index("ix_mistakes_question_id", "mistakes", ["question_id"])
    op.create_index("ix_mistakes_attempt_id", "mistakes", ["attempt_id"])

    op.create_table(
        "mastery_states",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("twin_id", sa.String(length=36), nullable=False),
        sa.Column("kp_id", sa.String(length=36), nullable=False),
        sa.Column("p_mastery", sa.Float(), nullable=False, server_default="0.25"),
        sa.Column("ability_elo", sa.Float(), nullable=False, server_default="1200.0"),
        sa.Column("stability", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("difficulty_fsrs", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("last_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["kp_id"], ["knowledge_points.id"]),
        sa.ForeignKeyConstraint(["twin_id"], ["learning_twins.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mastery_states_user_id", "mastery_states", ["user_id"])
    op.create_index("ix_mastery_states_twin_id", "mastery_states", ["twin_id"])
    op.create_index("ix_mastery_states_kp_id", "mastery_states", ["kp_id"])

    op.create_table(
        "study_plans",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("twin_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="queued"),
        sa.Column("profile_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("candidates_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("chosen_route_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("narrative", sa.Text(), nullable=False, server_default=""),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["twin_id"], ["learning_twins.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_study_plans_user_id", "study_plans", ["user_id"])
    op.create_index("ix_study_plans_twin_id", "study_plans", ["twin_id"])

    op.create_table(
        "plan_tasks",
        sa.Column("plan_id", sa.String(length=36), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("kp_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("question_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("est_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("completion_criteria", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["study_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_tasks_plan_id", "plan_tasks", ["plan_id"])

    op.create_table(
        "blackboard_lessons",
        sa.Column("twin_id", sa.String(length=36), nullable=False),
        sa.Column("topic", sa.String(length=240), nullable=False),
        sa.Column("kp_id", sa.String(length=36), nullable=True),
        sa.Column("steps_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("model", sa.String(length=120), nullable=False, server_default="template-fallback"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["kp_id"], ["knowledge_points.id"]),
        sa.ForeignKeyConstraint(["twin_id"], ["learning_twins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blackboard_lessons_twin_id", "blackboard_lessons", ["twin_id"])
    op.create_index("ix_blackboard_lessons_topic", "blackboard_lessons", ["topic"])
    op.create_index("ix_blackboard_lessons_kp_id", "blackboard_lessons", ["kp_id"])


def downgrade() -> None:
    op.drop_index("ix_blackboard_lessons_kp_id", table_name="blackboard_lessons")
    op.drop_index("ix_blackboard_lessons_topic", table_name="blackboard_lessons")
    op.drop_index("ix_blackboard_lessons_twin_id", table_name="blackboard_lessons")
    op.drop_table("blackboard_lessons")
    op.drop_index("ix_plan_tasks_plan_id", table_name="plan_tasks")
    op.drop_table("plan_tasks")
    op.drop_index("ix_study_plans_twin_id", table_name="study_plans")
    op.drop_index("ix_study_plans_user_id", table_name="study_plans")
    op.drop_table("study_plans")
    op.drop_index("ix_mastery_states_kp_id", table_name="mastery_states")
    op.drop_index("ix_mastery_states_twin_id", table_name="mastery_states")
    op.drop_index("ix_mastery_states_user_id", table_name="mastery_states")
    op.drop_table("mastery_states")
    op.drop_index("ix_mistakes_attempt_id", table_name="mistakes")
    op.drop_index("ix_mistakes_question_id", table_name="mistakes")
    op.drop_index("ix_mistakes_twin_id", table_name="mistakes")
    op.drop_index("ix_mistakes_user_id", table_name="mistakes")
    op.drop_table("mistakes")
    op.drop_index("ix_attempts_question_id", table_name="attempts")
    op.drop_index("ix_attempts_twin_id", table_name="attempts")
    op.drop_index("ix_attempts_user_id", table_name="attempts")
    op.drop_table("attempts")
    op.drop_index("ix_questions_twin_id", table_name="questions")
    op.drop_index("ix_questions_user_id", table_name="questions")
    op.drop_table("questions")
    op.drop_index("ix_chunk_kp_kp_id", table_name="chunk_kp")
    op.drop_index("ix_chunk_kp_chunk_id", table_name="chunk_kp")
    op.drop_index("ix_chunk_kp_twin_id", table_name="chunk_kp")
    op.drop_index("ix_chunk_kp_user_id", table_name="chunk_kp")
    op.drop_table("chunk_kp")
    op.drop_index("ix_kp_edges_to_kp_id", table_name="kp_edges")
    op.drop_index("ix_kp_edges_from_kp_id", table_name="kp_edges")
    op.drop_index("ix_kp_edges_twin_id", table_name="kp_edges")
    op.drop_index("ix_kp_edges_user_id", table_name="kp_edges")
    op.drop_table("kp_edges")
    op.drop_index("ix_knowledge_points_parent_id", table_name="knowledge_points")
    op.drop_index("ix_knowledge_points_name", table_name="knowledge_points")
    op.drop_index("ix_knowledge_points_twin_id", table_name="knowledge_points")
    op.drop_index("ix_knowledge_points_user_id", table_name="knowledge_points")
    op.drop_table("knowledge_points")
    op.drop_column("learning_records", "payload_json")
    op.drop_column("learning_twins", "profile_json")
    op.drop_column("learning_twins", "xp")
    op.drop_column("learning_twins", "level")
