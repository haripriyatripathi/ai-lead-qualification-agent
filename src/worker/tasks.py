"""Celery tasks for lead processing."""
import json
import logging

from src.db.models import Lead, LeadEvent
from src.logging_config import configure_logging
from src.services.enrichment import enrich_from_domain
from src.services.llm import LLMService
from src.services.scoring import ScoringService

configure_logging()
from src.db.session_sync import get_sync_session
from src.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _lead_payload_to_dict(raw_payload: str | bytes) -> dict:
    """Convert stored raw_payload (string) to dict for LLM. Safe fallback if not JSON."""
    if isinstance(raw_payload, bytes):
        raw_payload = raw_payload.decode("utf-8", errors="replace")
    s = raw_payload.strip() if isinstance(raw_payload, str) else str(raw_payload)
    try:
        out = json.loads(s)
        return out if isinstance(out, dict) else {"raw": s}
    except (json.JSONDecodeError, TypeError):
        return {"raw": s}


@celery_app.task(name="process_lead", bind=True, max_retries=3)
def process_lead(self, lead_id: str) -> None:
    """Process a lead: fetch, analyze via Ollama (Llama3), log result, mark processed. No DB store of analysis yet."""
    session = get_sync_session()
    try:
        lead = session.get(Lead, int(lead_id))
        if not lead:
            logger.error("Lead not found lead_id=%s", lead_id)
            return

        logger.info("Processing lead %s", lead_id)

        payload_dict = _lead_payload_to_dict(lead.raw_payload)
        email = (payload_dict.get("email") or payload_dict.get("contact_email") or "").strip()
        website_metadata = {}
        if email and "@" in email:
            try:
                website_metadata = enrich_from_domain(email)
                if website_metadata.get("domain") and (website_metadata.get("title") or website_metadata.get("text_snippet")):
                    logger.info("Enrichment for lead_id=%s domain=%s", lead_id, website_metadata.get("domain"))
            except Exception as e:
                logger.warning("Enrichment failed lead_id=%s: %s", lead_id, e)

        has_website_metadata = bool(
            website_metadata
            and (website_metadata.get("title") or website_metadata.get("description") or website_metadata.get("text_snippet"))
        )

        llm = LLMService()
        extracted = None
        try:
            extracted = llm.analyze_lead(payload_dict, website_metadata=website_metadata or None)
        except ValueError as parse_err:
            logger.warning("LLM JSON parse failed lead_id=%s, retrying with simplified prompt: %s", lead_id, parse_err)
            try:
                extracted = llm.analyze_lead(payload_dict, website_metadata=None, use_simplified_prompt=True)
            except Exception as retry_exc:
                logger.exception("Ollama analyze_lead retry failed lead_id=%s: %s", lead_id, retry_exc)
                session.close()
                raise self.retry(exc=retry_exc)
        except Exception as exc:
            logger.exception("Ollama analyze_lead failed lead_id=%s: %s", lead_id, exc)
            session.close()
            raise self.retry(exc=exc)

        logger.info("Lead analysis result lead_id=%s extracted=%s", lead_id, extracted)

        try:
            session.add(LeadEvent(lead_id=lead.id, event_type="lead_analyzed", payload=extracted))
        except Exception as e:
            logger.warning("Failed to insert lead_analyzed event lead_id=%s: %s", lead_id, e)

        # Merge email from payload into extracted for email trust scoring
        email_for_trust = (
            extracted.get("email") or extracted.get("contact_email")
            or payload_dict.get("email") or payload_dict.get("contact_email")
            or ""
        )
        extracted = {**extracted, "email": email_for_trust}
        final_score, priority, breakdown, confidence_score = ScoringService.compute_score(
            extracted, has_website_metadata=has_website_metadata
        )

        # Final validation: clamp score 0-100
        final_score = min(100, max(0, final_score))
        intent_category = (extracted.get("intent_category") or "").strip()
        if intent_category == "Academic":
            final_score = 0
            priority = "Rejected"
        # Downgrade High to Medium if confidence too low
        if confidence_score is not None and confidence_score < 40 and priority == "High":
            original_priority = priority
            priority = "Medium"
            try:
                session.add(
                    LeadEvent(
                        lead_id=lead.id,
                        event_type="validation_adjustment",
                        payload={
                            "reason": "confidence_score_below_40",
                            "confidence_score": confidence_score,
                            "original_priority": original_priority,
                            "adjusted_priority": priority,
                        },
                    )
                )
                logger.info(
                    "Validation: downgraded lead_id=%s to Medium (confidence=%s)",
                    lead_id, confidence_score,
                )
            except Exception as e:
                logger.warning("Failed to insert validation_adjustment event lead_id=%s: %s", lead_id, e)

        lead.company_size = extracted.get("company_size") or None
        lead.industry = extracted.get("industry") or None
        lead.role_level = extracted.get("authority_level") or extracted.get("role_level") or None
        lead.intent_score = breakdown.get("intent")  # 5-category model: intent points 0-15
        lead.urgency_level = None  # Not in new schema; kept for DB compatibility
        lead.final_score = final_score
        lead.priority = priority
        lead.confidence_score = confidence_score
        lead.processed = True

        # Message summary (all leads): 5–10 word LLM summary
        message_text = (
            payload_dict.get("message")
            or payload_dict.get("body")
            or payload_dict.get("inquiry")
            or (payload_dict.get("raw") if isinstance(payload_dict.get("raw"), str) else None)
            or json.dumps(payload_dict)[:2000]
        )
        if message_text and isinstance(message_text, str):
            try:
                summary = llm.summarize_message(message_text)
                if summary:
                    lead.message_summary = summary[:256]
                    logger.info("Message summary for lead_id=%s: %s", lead_id, summary[:80])
            except Exception as e:
                logger.warning("Summarize message failed lead_id=%s: %s", lead_id, e)
        else:
            try:
                summary = llm.summarize_message(str(payload_dict)[:2000])
                if summary:
                    lead.message_summary = summary[:256]
            except Exception as e:
                logger.warning("Summarize message failed lead_id=%s: %s", lead_id, e)

        # AI email draft for High priority only (View/Edit/Send from dashboard)
        if priority == "High":
            try:
                lead_payload = {
                    **payload_dict,
                    "name": payload_dict.get("name") or payload_dict.get("contact_name"),
                    "company": payload_dict.get("company") or payload_dict.get("company_name"),
                    "role": payload_dict.get("role") or payload_dict.get("job_title") or extracted.get("role_level"),
                    "message": message_text if isinstance(message_text, str) else str(payload_dict)[:1500],
                }
                draft_email = llm.generate_reply_email(lead_payload)
                if draft_email:
                    lead.ai_email_draft = draft_email
                    logger.info("AI email draft saved for lead_id=%s", lead_id)
            except Exception as e:
                logger.warning("Generate reply email failed lead_id=%s: %s", lead_id, e)

        try:
            session.add(
                LeadEvent(
                    lead_id=lead.id,
                    event_type="lead_scored",
                    payload={"final_score": final_score, "priority": priority, "confidence_score": confidence_score, **breakdown},
                )
            )
        except Exception as e:
            logger.warning("Failed to insert lead_scored event lead_id=%s: %s", lead_id, e)
        session.commit()
        logger.info(
            "Lead processed lead_id=%s final_score=%s priority=%s confidence=%s",
            lead_id, final_score, priority, confidence_score,
        )
    except Exception as exc:
        session.rollback()
        logger.exception("process_lead failed lead_id=%s", lead_id)
        raise self.retry(exc=exc)
    finally:
        session.close()


@celery_app.task(bind=True, max_retries=3)
def process_lead_task(self, lead_id: int) -> None:
    """Full pipeline: extract via LLM, score, notify, store. Uses sync DB in worker."""
    from src.services.pipeline import run_lead_pipeline

    try:
        run_lead_pipeline(lead_id)
    except Exception as exc:
        logger.exception("Lead pipeline failed lead_id=%s", lead_id)
        raise self.retry(exc=exc)
