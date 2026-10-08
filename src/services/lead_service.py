"""Lead domain service: create and persist leads (business logic out of API)."""
import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Lead, LeadEvent


def serialize_payload(raw: dict | str) -> str:
    """Store raw payload as string for DB."""
    if isinstance(raw, str):
        return raw
    return json.dumps(raw)


async def create_lead(
    *,
    source: str,
    raw_payload: dict | str,
    db: AsyncSession,
) -> Lead:
    """Create a lead and enqueued event; commit and return the lead. Caller must not add business logic."""
    raw_str = serialize_payload(raw_payload)
    lead = Lead(source=source, raw_payload=raw_str, status="pending")
    db.add(lead)
    await db.flush()
    db.add(LeadEvent(lead_id=lead.id, event_type="lead_received", payload=None))
    db.add(LeadEvent(lead_id=lead.id, event_type="enqueued", payload={"queued": True}))
    await db.commit()
    await db.refresh(lead)
    return lead


async def get_leads_list(db: AsyncSession) -> list[Lead]:
    """Return all leads ordered by created_at desc for dashboard list."""
    result = await db.execute(
        select(Lead).order_by(Lead.created_at.desc())
    )
    return list(result.scalars().all())


async def get_analytics(db: AsyncSession) -> dict:
    """
    Return aggregate analytics: total_leads, high/medium/low_priority counts, average_score.
    Computed from DB; scores are from final_score (nullable), priority from priority column.
    """
    total = await db.execute(select(func.count(Lead.id)))
    total_leads = total.scalar() or 0

    high = await db.execute(select(func.count(Lead.id)).where(Lead.priority == "High"))
    medium = await db.execute(select(func.count(Lead.id)).where(Lead.priority == "Medium"))
    low = await db.execute(
        select(func.count(Lead.id)).where(Lead.priority.in_(["Low", "Very Low", "Rejected"]))
    )
    high_priority = high.scalar() or 0
    medium_priority = medium.scalar() or 0
    low_priority = low.scalar() or 0

    avg_row = await db.execute(select(func.avg(Lead.final_score)).where(Lead.final_score.isnot(None)))
    avg_val = avg_row.scalar()
    average_score = round(float(avg_val or 0), 2)

    return {
        "total_leads": total_leads,
        "high_priority": high_priority,
        "medium_priority": medium_priority,
        "low_priority": low_priority,
        "average_score": average_score,
    }
