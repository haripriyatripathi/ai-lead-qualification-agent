"""Unit tests for scoring logic."""
import pytest

from src.schemas.lead import ExtractedLead
from src.services.scoring import compute_score, get_segment


def test_compute_score_high():
    extracted = ExtractedLead(
        company_name="Acme",
        company_size_bucket="201+",
        industry="SaaS",
        role="VP Engineering",
        intent_signals="wants enterprise demo",
        contact_email="vp@acme.com",
    )
    assert compute_score(extracted) >= 70


def test_compute_score_low():
    extracted = ExtractedLead(
        company_name="Small Co",
        company_size_bucket="1-10",
        industry="Other",
        role="Intern",
        intent_signals="",
        contact_email="",
    )
    assert compute_score(extracted) < 40


def test_compute_score_mid():
    extracted = ExtractedLead(
        company_name="Mid",
        company_size_bucket="11-50",
        industry="technology",
        role="Developer",
        intent_signals="interested",
        contact_email="dev@mid.com",
    )
    score = compute_score(extracted)
    assert 40 <= score < 70


def test_get_segment():
    assert get_segment(80) == "hot"
    assert get_segment(70) == "hot"
    assert get_segment(50) == "warm"
    assert get_segment(40) == "warm"
    assert get_segment(30) == "cold"
