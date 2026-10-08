"""Add message_summary, ai_email_draft, email_sent, email_sent_at to leads.

Revision ID: 006
Revises: 005
Create Date: 2025-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("message_summary", sa.String(length=256), nullable=True))
    op.add_column("leads", sa.Column("ai_email_draft", sa.Text(), nullable=True))
    op.add_column("leads", sa.Column("email_sent", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("leads", sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "email_sent_at")
    op.drop_column("leads", "email_sent")
    op.drop_column("leads", "ai_email_draft")
    op.drop_column("leads", "message_summary")
