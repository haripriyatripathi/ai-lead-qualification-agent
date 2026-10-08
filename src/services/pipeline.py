"""Lead processing pipeline: extract, score, persist, notify."""
import logging

from sqlalchemy.orm import Session

from src.config import settings
from src.db.models import Lead, LeadEvent
from src.db.session_sync import get_sync_session
from src.schemas.lead import ExtractedLead
from src.services.email_sender import send_lead_notification
from src.services.llm import extract_lead
from src.services.scoring import compute_score, get_segment
from src.services.slack_notifier import send_slack_notification

logger = logging.getLogger(__name__)


def run_lead_pipeline(lead_id: int) -> None:
    """Load lead, extract via LLM, score, persist, and optionally notify."""
    session: Session = get_sync_session()
    try:
        lead = session.get(Lead, lead_id)
        if not lead:
            logger.error("Lead not found lead_id=%s", lead_id)
            return
        if lead.status != "pending":
            logger.info("Lead already processed lead_id=%s status=%s", lead_id, lead.status)
            return

        lead.status = "processing"
        session.add(LeadEvent(lead_id=lead_id, event_type="processing_started", payload={}))
        session.commit()

        # Extract
        extracted = extract_lead(lead.raw_payload)
        lead.extracted = extracted.model_dump()
        session.add(LeadEvent(lead_id=lead_id, event_type="extracted", payload=lead.extracted))
        session.commit()

        # Score
        score = compute_score(extracted)
        segment = get_segment(score)
        lead.score = score
        lead.status = "qualified" if score >= settings.score_threshold_notify else "rejected"
        session.add(
            LeadEvent(lead_id=lead_id, event_type="scored", payload={"score": score, "segment": segment})
        )
        session.commit()

        # Notify if above threshold
        if score >= settings.score_threshold_notify:
            company_name = extracted.company_name or "Unknown"
            if send_lead_notification(lead_id, company_name, extracted, score):
                session.add(LeadEvent(lead_id=lead_id, event_type="email_sent", payload={}))
            if send_slack_notification(lead_id, company_name, extracted, score):
                session.add(LeadEvent(lead_id=lead_id, event_type="slack_sent", payload={}))
            session.commit()

        logger.info("Pipeline completed lead_id=%s score=%s", lead_id, score)
    except Exception:
        session.rollback()
        lead = session.get(Lead, lead_id)
        if lead:
            lead.status = "failed"
            session.add(LeadEvent(lead_id=lead_id, event_type="failed", payload={"error": "pipeline exception"}))
            session.commit()
        raise
    finally:
        session.close()
