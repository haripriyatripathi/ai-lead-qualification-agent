"""Ollama client and structured lead extraction."""
import json
import logging
import re

import httpx

from src.config import settings
from src.schemas.lead import ExtractedLead

logger = logging.getLogger(__name__)

# Model for lead analysis (configurable via OLLAMA_MODEL).
# LLM returns classifications only; scoring math is deterministic in ScoringService.

AUTHORITY_LEVELS = ("C-Level", "VP", "Director", "Manager", "Individual Contributor", "IC", "Student", "Unknown")
INTENT_CATEGORIES = ("Active Buying", "Evaluation", "Researching", "Casual", "Academic")
FIRMOGRAPHIC_FIT_LEVELS = ("High Fit", "Medium Fit", "Low Fit")
TECH_OPPORTUNITY_LEVELS = ("Strong Opportunity", "Some Opportunity", "No Clear Opportunity")
COMPANY_SIZES = ("Startup", "SME", "Enterprise", "Unknown")

ANALYZE_LEAD_PROMPT = """You are a B2B lead qualification AI. Classify the lead only. Do NOT output any score or number.
Return ONLY strict JSON with these exact keys (no markdown, no extra text):

authority_level: One of ["C-Level", "VP", "Director", "Manager", "Individual Contributor", "Student", "Unknown"]
  (Classify job title into one of these; normalize messy titles.)
firmographic_fit: One of ["High Fit", "Medium Fit", "Low Fit"]
  (Is this company a good fit for AI automation SaaS? Use company name, domain, website, and lead message.)
tech_opportunity: One of ["Strong Opportunity", "Some Opportunity", "No Clear Opportunity"]
  (Based on detected technologies on their website, is there opportunity for modernization or AI automation?)
intent_category: One of ["Active Buying", "Evaluation", "Researching", "Casual", "Academic"]
  (Active Buying = budget, timeline, ASAP; Academic/Student = disqualified.)
intent_reasoning: short explanation (one sentence)
company_size: One of ["Startup", "SME", "Enterprise", "Unknown"]
industry: string (industry or sector)

Lead data (message, job title, company, etc.):
---
{lead_section}
---
{website_section}
{tech_section}

Strict JSON only. No markdown. No extra text."""

ANALYZE_LEAD_WEBSITE_BLOCK = """
Website metadata (use for firmographic_fit and context):
- Title: {title}
- Meta description: {description}
- Text snippet: {text_snippet}
"""

ANALYZE_LEAD_TECH_BLOCK = """
Detected technologies on website: {detected_tech}
Use this to answer tech_opportunity: Is there opportunity for modernization or AI automation? Strong / Some / No Clear.
"""

# Fallback prompt when full JSON parsing fails
ANALYZE_LEAD_PROMPT_SIMPLIFIED = """Classify this lead. Return ONLY a JSON object with these exact keys (no other text):
authority_level, firmographic_fit, tech_opportunity, intent_category, intent_reasoning, company_size, industry.
authority_level: C-Level, VP, Director, Manager, Individual Contributor, Student, Unknown.
firmographic_fit: High Fit, Medium Fit, Low Fit.
tech_opportunity: Strong Opportunity, Some Opportunity, No Clear Opportunity.
intent_category: Active Buying, Evaluation, Researching, Casual, Academic.
Lead data:
---
{lead_section}
---
Return valid JSON only."""


def _parse_json_strict(text: str) -> dict:
    """Extract a single JSON object from response; raise ValueError if invalid."""
    text = text.strip()
    # Strip optional markdown code fence
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object in response")
    depth = 0
    in_string = None  # " or ' when inside a string
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if in_string:
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == in_string:
                in_string = None
            continue
        if c in ('"', "'"):
            in_string = c
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    # Unclosed object (e.g. truncated response): try closing braces and parse
    if depth > 0:
        try:
            repaired = text[start:] + "}" * depth
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
    raise ValueError("Invalid JSON: unclosed object")


class LLMService:
    """Ollama-based service for lead analysis (Llama3)."""

    def __init__(self, base_url: str | None = None, timeout_seconds: int | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = timeout_seconds if timeout_seconds is not None else settings.ollama_timeout_seconds

    def analyze_lead(
        self,
        raw_payload: dict,
        website_metadata: dict | None = None,
        use_simplified_prompt: bool = False,
    ) -> dict:
        """
        Call Ollama to classify lead and infer firmographics.
        website_metadata: optional dict from enrichment.
        use_simplified_prompt: if True, use shorter prompt (for retry after parse failure).
        Returns single merged structured JSON. Raises on HTTP errors or invalid JSON.
        """
        url = f"{self.base_url}/api/generate"
        lead_section = json.dumps(raw_payload) if isinstance(raw_payload, dict) else str(raw_payload)
        lead_section = lead_section[:4000]

        if use_simplified_prompt:
            prompt = ANALYZE_LEAD_PROMPT_SIMPLIFIED.format(lead_section=lead_section)
        else:
            if website_metadata:
                ws = website_metadata
                website_section = ANALYZE_LEAD_WEBSITE_BLOCK.format(
                    title=(ws.get("title") or "")[:500],
                    description=(ws.get("description") or "")[:800],
                    text_snippet=(ws.get("text_snippet") or "")[:1500],
                )
                detected = ws.get("detected_tech") or []
                tech_str = ", ".join(detected) if isinstance(detected, list) else str(detected)
                if not tech_str:
                    tech_str = "None detected"
                tech_section = ANALYZE_LEAD_TECH_BLOCK.format(detected_tech=tech_str)
            else:
                website_section = ""
                tech_section = "\nDetected technologies on website: None (no enrichment)\n"
            prompt = ANALYZE_LEAD_PROMPT.format(
                lead_section=lead_section,
                website_section=website_section,
                tech_section=tech_section,
            )

        model = settings.ollama_model
        body = {"model": model, "prompt": prompt, "stream": False}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=body)
                if resp.status_code == 404:
                    msg = (
                        f"Ollama 404 at {url}. Ensure Ollama is running and model is pulled "
                        f"(e.g. 'ollama pull {model}'). Response: {resp.text[:500]!r}"
                    )
                    logger.error(msg)
                    resp.raise_for_status()
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            logger.exception("Ollama analyze_lead request failed: %s", e)
            raise

        text = data.get("response", "") or ""
        try:
            parsed = _parse_json_strict(text)
        except (ValueError, json.JSONDecodeError) as e:
            logger.exception("Invalid JSON from Ollama analyze_lead: %s", e)
            raise ValueError(f"Ollama returned invalid JSON: {e}") from e

        # Normalize and validate classification fields (strict). No scoring here.
        authority = (parsed.get("authority_level") or "Unknown").strip()
        if authority == "IC":
            authority = "Individual Contributor"
        firmographic_fit = (parsed.get("firmographic_fit") or "Low Fit").strip()
        tech_opportunity = (parsed.get("tech_opportunity") or "No Clear Opportunity").strip()
        intent = (parsed.get("intent_category") or "Casual").strip()
        intent_reasoning = (parsed.get("intent_reasoning") or parsed.get("reasoning") or "").strip()
        company_size = (parsed.get("company_size") or "Unknown").strip()
        industry = (parsed.get("industry") or "").strip()

        if authority not in AUTHORITY_LEVELS:
            authority = "Unknown"
        if intent not in INTENT_CATEGORIES:
            intent = "Casual"
        if firmographic_fit not in FIRMOGRAPHIC_FIT_LEVELS:
            firmographic_fit = "Low Fit"
        if tech_opportunity not in TECH_OPPORTUNITY_LEVELS:
            tech_opportunity = "No Clear Opportunity"
        if company_size not in COMPANY_SIZES:
            company_size = "Unknown"

        return {
            "authority_level": authority,
            "firmographic_fit": firmographic_fit,
            "tech_opportunity": tech_opportunity,
            "intent_category": intent,
            "intent_reasoning": intent_reasoning,
            "company_size": company_size,
            "industry": industry,
            "reasoning": intent_reasoning,
            # Backward compatibility for DB/display
            "role_level": authority,
            "summary": intent_reasoning,
        }

    def summarize_message(self, message: str) -> str:
        """Generate a 5–10 word summary of the lead message. Returns plain text."""
        if not (message or "").strip():
            return ""
        prompt = SUMMARY_MESSAGE_PROMPT.format(message=(message or "")[:2000])
        url = f"{self.base_url}/api/generate"
        body = {"model": settings.ollama_model, "prompt": prompt, "stream": False}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=body)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            logger.exception("Ollama summarize_message failed: %s", e)
            return ""
        text = (data.get("response") or "").strip()
        return text[:256] if text else ""

    def generate_reply_email(self, lead_data: dict) -> str:
        """Generate a short reply email from lead context. Returns plain text."""
        name = (lead_data.get("name") or lead_data.get("contact_name") or "").strip() or "there"
        company = (lead_data.get("company") or lead_data.get("company_name") or "").strip() or "your company"
        role = (lead_data.get("role") or lead_data.get("role_level") or lead_data.get("job_title") or "").strip() or "your role"
        message = (lead_data.get("message") or lead_data.get("raw") or str(lead_data)[:1500]).strip() or "Their inquiry"
        prompt = REPLY_EMAIL_PROMPT.format(name=name, company=company, role=role, message=message[:1000])
        url = f"{self.base_url}/api/generate"
        body = {"model": settings.ollama_model, "prompt": prompt, "stream": False}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=body)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            logger.exception("Ollama generate_reply_email failed: %s", e)
            return _fallback_reply_email(name, company, role)
        text = (data.get("response") or "").strip()
        return text if text else _fallback_reply_email(name, company, role)

    def generate_outreach_email(self, extracted: dict) -> str:
        """
        Generate a professional B2B outreach email (plain text) from extracted lead data.
        References company industry and role, mentions AI automation solution. Kept concise.
        """
        industry = (extracted.get("industry") or "").strip() or "your industry"
        role = (extracted.get("role_level") or "").strip() or "your role"
        summary = (extracted.get("summary") or "").strip() or "your interest"
        prompt = OUTREACH_EMAIL_PROMPT.format(
            industry=industry,
            role=role,
            summary=summary[:500],
        )
        url = f"{self.base_url}/api/generate"
        body = {"model": settings.ollama_model, "prompt": prompt, "stream": False}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=body)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            logger.exception("Ollama generate_outreach_email failed: %s", e)
            raise
        text = (data.get("response") or "").strip()
        return text if text else _fallback_outreach_email(industry, role)


SUMMARY_MESSAGE_PROMPT = """You are summarizing a sales inquiry.
Create a concise 5–10 word summary describing what the lead wants.
Return plain text only.

Lead message:
---
{message}
---

Summary:"""

REPLY_EMAIL_PROMPT = """You are a professional B2B sales assistant.
Write a short reply email responding to the lead inquiry.

Context:
Name: {name}
Company: {company}
Role: {role}
Message: {message}

Instructions:
- Thank them for reaching out
- Acknowledge their request
- Mention AI automation solutions
- Suggest scheduling a call
- Keep under 120 words
- Professional but friendly tone
- Return plain text only.

Email body:"""

OUTREACH_EMAIL_PROMPT = """Write a short, professional B2B outreach email (plain text only, no HTML).
- Address the reader by their role in {role} and reference {industry}.
- Briefly mention an AI automation solution that could help their business.
- Keep it concise (3-4 sentences).
- Do not use markdown, bullets, or subject line—output only the email body.
- Tone: professional and helpful.

Email body:"""


def _fallback_reply_email(name: str, company: str, role: str) -> str:
    """Fallback reply body when LLM does not return content."""
    return (
        f"Hi {name},\n\n"
        f"Thank you for reaching out. We'd be glad to discuss how AI automation solutions could help {company}. "
        f"Would you be available for a short call this week?\n\nBest regards"
    )


def _fallback_outreach_email(industry: str, role: str) -> str:
    """Fallback body when LLM does not return content."""
    return (
        f"Hello,\n\n"
        f"We noticed your interest in {industry} and your role in {role}. "
        f"We offer AI-powered automation solutions that could help streamline your operations. "
        f"Would you be open to a brief conversation?\n\nBest regards"
    )


EXTRACTION_PROMPT = """You are a B2B lead analyst. Extract structured data from the following lead information.
Output ONLY a single JSON object with these exact keys (use empty string if unknown):
- company_name
- company_size_bucket (one of: "1-10", "11-50", "51-200", "201+", or "")
- industry
- role (job title or role)
- intent_signals (brief summary of buying intent or interest)
- contact_email

Lead data:
---
{raw_payload}
---

JSON only, no markdown or explanation:"""


def extract_lead(raw_payload: str) -> ExtractedLead:
    """Call Ollama to extract structured lead data; parse and return ExtractedLead."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": EXTRACTION_PROMPT.format(raw_payload=raw_payload[:4000]),
        "stream": False,
    }
    try:
        with httpx.Client(timeout=settings.ollama_timeout_seconds) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.exception("Ollama request failed: %s", e)
        raise

    text = data.get("response", "") or ""

    # Try to parse JSON from response (handle markdown code blocks)
    parsed = _parse_json_from_response(text)
    if parsed is None:
        logger.warning("Could not parse JSON from LLM response, using empty extraction")
        return ExtractedLead()
    try:
        return ExtractedLead(**parsed)
    except Exception as e:
        logger.warning("ExtractedLead validation failed: %s, using partial", e)
        return ExtractedLead(**{k: parsed.get(k, "") for k in ExtractedLead.model_fields})


def _parse_json_from_response(text: str) -> dict | None:
    """Extract JSON object from model output, optionally inside ```json ... ```."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    # Find first { ... }
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        return None
