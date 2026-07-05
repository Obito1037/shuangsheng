"""M3 blackboard cache profile hash.

Revision ID: 20260705_0002
Revises: 20260705_0001
Create Date: 2026-07-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260705_0002"
down_revision = "20260705_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("blackboard_lessons", sa.Column("profile_hash", sa.String(length=64), nullable=False, server_default=""))
    op.create_index("ix_blackboard_lessons_profile_hash", "blackboard_lessons", ["profile_hash"])


def downgrade() -> None:
    op.drop_index("ix_blackboard_lessons_profile_hash", table_name="blackboard_lessons")
    op.drop_column("blackboard_lessons", "profile_hash")
