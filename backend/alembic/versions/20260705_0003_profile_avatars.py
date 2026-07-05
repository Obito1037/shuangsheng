"""User and twin avatar fields.

Revision ID: 20260705_0003
Revises: 20260705_0002
Create Date: 2026-07-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260705_0003"
down_revision = "20260705_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_data_url", sa.Text(), nullable=False, server_default=""))
    op.add_column("learning_twins", sa.Column("avatar_data_url", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("learning_twins", "avatar_data_url")
    op.drop_column("users", "avatar_data_url")
