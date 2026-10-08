"""Lead ingestion and retrieval routes. Business logic in services; routes only orchestrate."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_db
from src.db.models import Lead
from src.schemas.lead import LeadEmailOut, LeadIn, LeadListItem, LeadOut, SendEmailIn
from src.services.email_sender import EmailSender
from src.services.lead_service import create_lead as create_lead_service, get_leads_list
from src.worker.tasks import process_lead

router = APIRouter(prefix="/leads", tags=["leads"])
logger = logging.getLogger(__name__)


def _payload_name_company(raw_payload: str) -> tuple[str | None, str | None]:
    """Parse raw_payload and return (name, company) from common keys."""
    try:
        payload = json.loads(raw_payload) if isinstance(raw_payload, str) else (raw_payload or {})
        name = payload.get("name") or payload.get("contact_name") or None
        company = payload.get("company") or payload.get("company_name") or None
        return (str(name).strip() or None, str(company).strip() or None)
    except (TypeError, json.JSONDecodeError):
        return (None, None)


@router.get("", response_model=list[LeadListItem])
async def list_leads(db: AsyncSession = Depends(get_db)) -> list[LeadListItem]:
    """Return list of leads for dashboard with name/company from payload + analysis fields."""
    leads = await get_leads_list(db)
    result = []
    for lead in leads:
        name, company = _payload_name_company(lead.raw_payload)
        result.append(
            LeadListItem(
                id=lead.id,
                name=name,
                company=company,
                company_size=lead.company_size,
                industry=lead.industry,
                role_level=lead.role_level,
                intent_score=lead.intent_score,
                final_score=lead.final_score,
                priority=lead.priority,
                confidence_score=lead.confidence_score,
                message_summary=lead.message_summary,
                ai_email_draft=lead.ai_email_draft,
                email_sent=lead.email_sent or False,
                created_at=lead.created_at,
            )
        )
    return result


@router.post("", status_code=202)
async def create_lead(body: LeadIn, db: AsyncSession = Depends(get_db)) -> dict:
    """Accept a lead, persist via service, enqueue process_lead task; return 202 with lead id."""
    lead = await create_lead_service(source=body.source, raw_payload=body.raw_payload, db=db)
    process_lead.delay(str(lead.id))
    logger.info("Lead enqueued lead_id=%s", lead.id)
    return {"id": lead.id, "status": "accepted"}


@router.get("/{lead_id}/email", response_model=LeadEmailOut)
async def get_lead_email(lead_id: int, db: AsyncSession = Depends(get_db)) -> LeadEmailOut:
    """Return draft email and sent status for a lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadEmailOut(
        lead_id=lead.id,
        draft_email=lead.ai_email_draft or "",
        email_sent=lead.email_sent or False,
    )


@router.post("/{lead_id}/send-email")
async def send_lead_email(
    lead_id: int,
    body: SendEmailIn,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send email to lead: use edited_email if provided, else ai_email_draft. Update email_sent and email_sent_at."""
    from datetime import datetime, timezone

    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.email_sent:
        return {"ok": True, "message": "Email already sent"}
    try:
        payload = json.loads(lead.raw_payload) if isinstance(lead.raw_payload, str) else (lead.raw_payload or {})
    except (TypeError, json.JSONDecodeError):
        payload = {}
    to_email = (payload.get("email") or payload.get("contact_email") or "").strip()
    if not to_email or "@" not in to_email:
        raise HTTPException(status_code=400, detail="Lead has no valid email address")
    body_text = (body.edited_email or "").strip() or (lead.ai_email_draft or "").strip()
    if not body_text:
        raise HTTPException(status_code=400, detail="No draft or edited email to send")
    sender = EmailSender()
    sent, err_msg = sender.send_email(to_email, "Re: Your inquiry", body_text)
    if not sent:
        detail = err_msg
        if not detail:
            from src.config import settings
            if not (settings.smtp_host or "").strip():
                detail = "SMTP not configured. Create a .env file (copy from .env.example), set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL, then restart: docker compose up --build."
            elif not (settings.smtp_username or settings.smtp_user or "").strip() or not (settings.smtp_password or "").strip():
                detail = "SMTP credentials missing in .env. Set SMTP_USERNAME and SMTP_PASSWORD (for Gmail use an App Password)."
            else:
                detail = "Failed to send email; check SMTP configuration and try again."
        logger.warning("Send email failed lead_id=%s to=%s: %s", lead_id, to_email, detail)
        raise HTTPException(status_code=502, detail=detail)
    lead.email_sent = True
    lead.email_sent_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "message": "Email sent"}


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)) -> LeadOut:
    """Return lead by id with events."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id).options(selectinload(Lead.events)))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadOut.model_validate(lead)