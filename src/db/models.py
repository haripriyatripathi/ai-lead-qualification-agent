"""SQLAlchemy models for leads and events."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base for all models."""

    pass


class Lead(Base):
    """B2B lead record."""

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="api")
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # AI analysis and scoring (nullable)
    company_size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    intent_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    urgency_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    final_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message_summary: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ai_email_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    events: Mapped[list["LeadEvent"]] = relationship(
        "LeadEvent",
        back_populates="lead",
        order_by="LeadEvent.created_at",
        cascade="all, delete-orphan",
    )


class LeadEvent(Base):
    """Event log for lead processing steps (event-driven audit)."""

    __tablename__ = "lead_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    lead: Mapped["Lead"] = relationship("Lead", back_populates="events")


class ScoringRule(Base):
    """Configurable rule for scoring (e.g. role_level, urgency, company_size)."""

    __tablename__ = "scoring_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_value: Mapped[str] = mapped_column(String(128), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
