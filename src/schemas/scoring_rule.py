"""Pydantic schemas for scoring rules API."""

from pydantic import BaseModel


class ScoringRuleOut(BaseModel):
    """Scoring rule response."""

    id: int
    rule_type: str
    rule_value: str
    weight: int
    active: bool

    model_config = {"from_attributes": True}


class ScoringRuleUpdate(BaseModel):
    """Payload for updating a scoring rule (weight and active)."""

    weight: int
    active: bool
