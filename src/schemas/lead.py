"""Lead-related Pydantic schemas."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LeadIn(BaseModel):
    """Incoming lead payload (flexible JSON)."""

    source: str = "api"
    raw_payload: dict[str, Any] | str  # API accepts dict or string; we store as string


class LeadOut(BaseModel):
    """Lead response with events."""

    id: int
    source: str
    raw_payload: str
    status: str
    processed: bool
    score: int | None
    extracted: dict[str, Any] | None
    company_size: str | None = None
    industry: str | None = None
    role_level: str | None = None
    intent_score: int | None = None
    urgency_level: str | None = None
    final_score: int | None = None
    priority: str | None = None
    confidence_score: int | None = None
    message_summary: str | None = None
    ai_email_draft: str | None = None
    email_sent: bool = False
    email_sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    events: list["LeadEventOut"] = []

    model_config = {"from_attributes": True}


class LeadListItem(BaseModel):
    """Lead row for dashboard list (id + name, company from payload + analysis fields + created_at)."""

    id: int
    name: str | None = None
    company: str | None = None
    company_size: str | None = None
    industry: str | None = None
    role_level: str | None = None
    intent_score: int | None = None
    final_score: int | None = None
    priority: str | None = None
    confidence_score: int | None = None
    message_summary: str | None = None
    ai_email_draft: str | None = None
    email_sent: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadEmailOut(BaseModel):
    """Response for GET /leads/{id}/email."""

    lead_id: int
    draft_email: str
    email_sent: bool


class SendEmailIn(BaseModel):
    """Body for POST /leads/{id}/send-email."""

    edited_email: str | None = None


class AnalyticsOut(BaseModel):
    """Aggregate analytics for dashboard."""

    total_leads: int
    high_priority: int
    medium_priority: int
    low_priority: int
    average_score: float


class LeadEventOut(BaseModel):
    """Lead event for API response."""

    id: int
    lead_id: int
    event_type: str
    payload: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Fix forward ref for LeadOut.events
LeadOut.model_rebuild()


class ExtractedLead(BaseModel):
    """Structured extraction from LLM (used in scoring and storage)."""

    company_name: str = ""
    company_size_bucket: str = ""  # e.g. "1-10", "11-50", "51-200", "201+"
    industry: str = ""
    role: str = ""
    intent_signals: str = ""
    contact_email: str = ""
