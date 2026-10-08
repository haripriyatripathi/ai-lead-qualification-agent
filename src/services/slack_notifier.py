"""Slack webhook notifier for qualified leads."""
import logging

import httpx

from src.config import settings
from src.schemas.lead import ExtractedLead

logger = logging.getLogger(__name__)


def send_slack_notification(lead_id: int, company_name: str, extracted: ExtractedLead, score: int) -> bool:
    """POST to Slack webhook with lead summary. Returns True if sent."""
    if not settings.enable_slack or not settings.slack_webhook_url.strip():
        logger.debug("Slack disabled or webhook not set, skipping")
        return False

    text = (
        f"*New qualified lead* #{lead_id}\n"
        f"• Company: {company_name or 'N/A'}\n"
        f"• Industry: {extracted.industry or 'N/A'}\n"
        f"• Role: {extracted.role or 'N/A'}\n"
        f"• Score: {score}\n"
        f"• Contact: {extracted.contact_email or 'N/A'}\n"
        f"• Intent: {extracted.intent_signals or 'N/A'}"
    )
    payload = {"text": text}

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(settings.slack_webhook_url, json=payload)
            resp.raise_for_status()
        logger.info("Slack notification sent lead_id=%s", lead_id)
        return True
    except Exception as e:
        logger.exception("Failed to send Slack notification lead_id=%s: %s", lead_id, e)
        return False
