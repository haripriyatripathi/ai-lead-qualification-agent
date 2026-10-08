"""Domain-based website metadata enrichment for firmographic inference."""
import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "mail.com",
    "aol.com",
}

REQUEST_TIMEOUT = 5
USER_AGENT = "LeadiAgent/1.0 (B2B lead enrichment)"

# Lightweight tech detection: keywords in HTML for tech gap / opportunity
TECH_KEYWORDS = {
    "react": "react",
    "angular": "angular",
    "vue": "vue",
    "wordpress": "wordpress",
    "shopify": "shopify",
    "aws": "aws",
    "azure": "azure",
    "gcp": "gcp",
    "jquery": "jquery",
    "php": "php",
    "laravel": "laravel",
}
LEGACY_PATTERNS = ("php 5", "jquery 1.", "jquery 2.", "angularjs 1.")


def _detect_tech_from_html(html: str) -> list[str]:
    """Scan HTML for tech stack signals; return list of detected tech names."""
    if not html:
        return []
    html_lower = html.lower()
    detected = []
    for keyword, label in TECH_KEYWORDS.items():
        if keyword in html_lower:
            detected.append(label)
    for legacy in LEGACY_PATTERNS:
        if legacy in html_lower:
            detected.append("legacy")
            break
    return list(dict.fromkeys(detected))  # dedupe order-preserving


def _domain_from_email(email: str) -> str | None:
    if not email or "@" not in email:
        return None
    return email.strip().split("@")[-1].lower()


def _visible_text(soup: BeautifulSoup, max_chars: int = 1000) -> str:
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars] if text else ""


def enrich_from_domain(email: str) -> dict:
    """
    Extract domain from email, fetch homepage HTML, return title, meta description, and text snippet.
    Ignores free email domains. On any error returns empty metadata; does not raise.
    """
    domain = _domain_from_email(email)
    if not domain or domain in FREE_EMAIL_DOMAINS:
        return {"domain": domain or "", "title": "", "description": "", "text_snippet": "", "detected_tech": []}

    url = f"https://{domain}"
    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
    except Exception as e:
        logger.warning("Enrichment fetch failed domain=%s: %s", domain, e)
        return {"domain": domain, "title": "", "description": "", "text_snippet": "", "detected_tech": []}

    try:
        soup = BeautifulSoup(html, "html.parser")
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()[:500]
        description = ""
        meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta and meta.get("content"):
            description = meta["content"].strip()[:1000]
        text_snippet = _visible_text(soup, 1000)
        detected_tech = _detect_tech_from_html(html)
        return {
            "domain": domain,
            "title": title,
            "description": description,
            "text_snippet": text_snippet,
            "detected_tech": detected_tech,
        }
    except Exception as e:
        logger.warning("Enrichment parse failed domain=%s: %s", domain, e)
        return {"domain": domain, "title": "", "description": "", "text_snippet": "", "detected_tech": []}
