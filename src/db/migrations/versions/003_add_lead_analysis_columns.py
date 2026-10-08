"""Add lead analysis and scoring columns.

Revision ID: 003
Revises: 002
Create Date: 2025-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("company_size", sa.String(length=64), nullable=True))
    op.add_column("leads", sa.Column("industry", sa.String(length=128), nullable=True))
    op.add_column("leads", sa.Column("role_level", sa.String(length=64), nullable=True))
    op.add_column("leads", sa.Column("intent_score", sa.Integer(), nullable=True))
    op.add_column("leads", sa.Column("urgency_level", sa.String(length=32), nullable=True))
    op.add_column("leads", sa.Column("final_score", sa.Integer(), nullable=True))
    op.add_column("leads", sa.Column("priority", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "priority")
    op.drop_column("leads", "final_score")
    op.drop_column("leads", "urgency_level")
    op.drop_column("leads", "intent_score")
    op.drop_column("leads", "role_level")
    op.drop_column("leads", "industry")
    op.drop_column("leads", "company_size")
