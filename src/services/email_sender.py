"""SMTP email sender for lead notifications."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import settings
from src.schemas.lead import ExtractedLead

logger = logging.getLogger(__name__)


def _safe_smtp_error(e: Exception) -> str:
    """Return a user-safe error message (no credentials or internal details)."""
    msg = (e.__class__.__name__ or str(e)).lower()
    if "auth" in msg or "authentication" in msg or "535" in str(e):
        return "SMTP authentication failed. For Gmail use an App Password (not your normal password)."
    if "connect" in msg or "refused" in msg or "timed out" in msg:
        return "SMTP connection failed. Check SMTP_HOST and SMTP_PORT (e.g. smtp.gmail.com, 587)."
    return "SMTP error. Check SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM_EMAIL."


class EmailSender:
    """Send emails via SMTP with TLS. Does not raise; logs success or failure."""

    def send_email(self, to_email: str, subject: str, body: str) -> tuple[bool, str | None]:
        """
        Send a plain-text email.
        Returns (True, None) if sent, (False, error_message) otherwise.
        error_message is safe to show to users (no credentials).
        """
        if not to_email or not to_email.strip():
            return (False, "Recipient email is missing.")
        if not settings.smtp_host or not (settings.smtp_host.strip()):
            logger.warning("SMTP not configured: SMTP_HOST is empty")
            return (
                False,
                "SMTP not configured. Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM_EMAIL in .env or Docker environment.",
            )
        username = (settings.smtp_username or settings.smtp_user or "").strip()
        if not username or not (settings.smtp_password or "").strip():
            return (
                False,
                "SMTP credentials missing. Set SMTP_USERNAME and SMTP_PASSWORD (for Gmail use an App Password) in .env.",
            )
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = settings.smtp_from_email or username
            msg["To"] = to_email.strip()
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                server.login(username, settings.smtp_password)
                server.sendmail(msg["From"], [to_email.strip()], msg.as_string())
            logger.info("Email sent to %s subject=%s", to_email, subject)
            return (True, None)
        except Exception as e:
            logger.exception("Failed to send email to %s: %s", to_email, e)
            return (False, _safe_smtp_error(e))


def send_lead_notification(lead_id: int, company_name: str, extracted: ExtractedLead, score: int) -> bool:
    """Send a simple HTML email for a qualified lead. Returns True if sent."""
    if not settings.enable_email or not settings.smtp_host:
        logger.debug("Email disabled or SMTP not configured, skipping")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"New qualified lead #{lead_id}: {company_name or 'Unknown'}"
    msg["From"] = settings.smtp_from_addr
    # In production you'd have a configured recipient
    msg["To"] = settings.smtp_from_addr

    text = (
        f"Lead ID: {lead_id}\n"
        f"Company: {company_name}\n"
        f"Industry: {extracted.industry}\n"
        f"Role: {extracted.role}\n"
        f"Score: {score}\n"
        f"Contact: {extracted.contact_email}\n"
        f"Intent: {extracted.intent_signals}\n"
    )
    html = f"""
    <html><body>
    <h2>New qualified lead #{lead_id}</h2>
    <p><b>Company:</b> {company_name or 'N/A'}</p>
    <p><b>Industry:</b> {extracted.industry or 'N/A'}</p>
    <p><b>Role:</b> {extracted.role or 'N/A'}</p>
    <p><b>Score:</b> {score}</p>
    <p><b>Contact:</b> {extracted.contact_email or 'N/A'}</p>
    <p><b>Intent:</b> {extracted.intent_signals or 'N/A'}</p>
    </body></html>
    """
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from_addr, [msg["To"]], msg.as_string())
        logger.info("Lead notification email sent lead_id=%s", lead_id)
        return True
    except Exception as e:
        logger.exception("Failed to send lead email lead_id=%s: %s", lead_id, e)
        return False
