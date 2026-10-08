"""Business scoring logic for extracted leads. Clean 5-category model (100 pts max)."""

from src.schemas.lead import ExtractedLead

# Email Trust (deterministic, 20 pts max)
FREE_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com"}

# Authority Level (LLM classification, 25 pts max)
AUTHORITY_SCORES = {
    "C-Level": 25,
    "VP": 25,
    "Director": 20,
    "Manager": 15,
    "Individual Contributor": 5,
    "IC": 5,
    "Student": 0,
    "Unknown": 5,
}

# Firmographic Fit (LLM inference, 25 pts max)
FIRMOGRAPHIC_SCORES = {
    "High Fit": 25,
    "Medium Fit": 15,
    "Low Fit": 5,
}

# Tech Gap (LLM + website analysis, 15 pts max)
TECH_OPPORTUNITY_SCORES = {
    "Strong Opportunity": 15,
    "Some Opportunity": 8,
    "No Clear Opportunity": 0,
}

# Intent Score (LLM, 15 pts max). Academic → 0 and disqualified.
INTENT_SCORES = {
    "Active Buying": 15,
    "Evaluation": 10,
    "Researching": 5,
    "Casual": 2,
    "Academic": 0,
}

# Keys required for confidence "fully structured" check
STRUCTURED_KEYS = (
    "authority_level",
    "firmographic_fit",
    "tech_opportunity",
    "intent_category",
    "company_size",
    "industry",
)
CLASSIFICATION_FIELDS = STRUCTURED_KEYS


def compute_email_trust(email: str) -> int:
    """
    Email Trust: Corporate domain 20, free email 5, suspicious/student 0.
    No AI; deterministic.
    """
    if not email or "@" not in email:
        return 0
    domain = email.strip().split("@")[-1].lower()
    if domain in FREE_DOMAINS:
        return 5
    if domain.endswith(".edu"):
        return 0
    return 20


def compute_confidence(
    extracted: dict,
    has_website_metadata: bool,
    email_trust: int,
) -> int:
    """
    Confidence score 0-100: +25 website metadata, +25 fully structured,
    +25 at least 3 classification fields non-empty, +25 email_trust == 20.
    """
    confidence = 0
    if has_website_metadata:
        confidence += 25
    structured = all(k in extracted and extracted.get(k) is not None for k in STRUCTURED_KEYS)
    if structured:
        confidence += 25
    non_empty = sum(1 for k in CLASSIFICATION_FIELDS if (extracted.get(k) or "").strip())
    if non_empty >= 3:
        confidence += 25
    if email_trust == 20:
        confidence += 25
    return min(100, confidence)


class ScoringService:
    """
    Final score = email_trust + authority + firmographic + tech + intent (cap 100).
    LLM outputs classifications only; all scoring math is deterministic here.
    """

    @staticmethod
    def compute_score(
        extracted: dict,
        has_website_metadata: bool = False,
    ) -> tuple[int, str, dict, int]:
        """
        Compute final score from 5 categories. Store breakdown as
        email_trust, authority, firmographic, tech, intent.
        If intent_category == "Academic": final_score = 0, priority = "Rejected".
        Else: 80+ High, 60-79 Medium, 40-59 Low, below 40 Very Low.
        Returns (final_score, priority, breakdown, confidence_score).
        """
        email = (extracted.get("email") or extracted.get("contact_email") or "").strip()
        authority_level = (extracted.get("authority_level") or extracted.get("role_level") or "Unknown").strip()
        if authority_level == "IC":
            authority_level = "Individual Contributor"
        firmographic_fit = (extracted.get("firmographic_fit") or "Low Fit").strip()
        tech_opportunity = (extracted.get("tech_opportunity") or "No Clear Opportunity").strip()
        intent_category = (extracted.get("intent_category") or "Casual").strip()

        email_trust = compute_email_trust(email)
        authority = AUTHORITY_SCORES.get(authority_level, AUTHORITY_SCORES["Unknown"])
        firmographic = FIRMOGRAPHIC_SCORES.get(firmographic_fit, FIRMOGRAPHIC_SCORES["Low Fit"])
        tech = TECH_OPPORTUNITY_SCORES.get(tech_opportunity, TECH_OPPORTUNITY_SCORES["No Clear Opportunity"])
        intent = INTENT_SCORES.get(intent_category, INTENT_SCORES["Casual"])

        confidence_score = compute_confidence(extracted, has_website_metadata, email_trust)

        # Breakdown stored in lead_events (clean keys)
        breakdown = {
            "email_trust": email_trust,
            "authority": authority,
            "firmographic": firmographic,
            "tech": tech,
            "intent": intent,
            "confidence_score": confidence_score,
            "authority_level": authority_level,
            "firmographic_fit": firmographic_fit,
            "tech_opportunity": tech_opportunity,
            "intent_category": intent_category,
        }

        if intent_category == "Academic":
            return (0, "Rejected", breakdown, confidence_score)

        total = email_trust + authority + firmographic + tech + intent
        final_score = min(100, max(0, total))

        if final_score >= 80:
            priority = "High"
        elif final_score >= 60:
            priority = "Medium"
        elif final_score >= 40:
            priority = "Low"
        else:
            priority = "Very Low"

        return (final_score, priority, breakdown, confidence_score)


# Legacy helpers (other callers)
TARGET_INDUSTRIES = {"technology", "saas", "software", "fintech", "healthtech", "enterprise"}
TARGET_SIZE_BUCKETS = {"51-200", "201+"}
SENIOR_ROLE_KEYWORDS = {"director", "vp", "vice president", "head of", "ceo", "cto", "founder"}


def compute_score(extracted: ExtractedLead) -> int:
    """Legacy: return a score 0-100 based on company size, industry, role, and intent."""
    score = 0
    if extracted.company_size_bucket in TARGET_SIZE_BUCKETS:
        score += 30
    elif extracted.company_size_bucket == "11-50":
        score += 15
    industry_lower = (extracted.industry or "").lower()
    if any(t in industry_lower for t in TARGET_INDUSTRIES):
        score += 25
    role_lower = (extracted.role or "").lower()
    if any(kw in role_lower for kw in SENIOR_ROLE_KEYWORDS):
        score += 25
    if (extracted.intent_signals or "").strip():
        score += 10
    if (extracted.contact_email or "").strip() and "@" in extracted.contact_email:
        score += 10
    return min(100, score)


def get_segment(score: int) -> str:
    """Return segment label from score."""
    if score >= 70:
        return "hot"
    if score >= 40:
        return "warm"
    return "cold"
