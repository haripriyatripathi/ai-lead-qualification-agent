"""Scoring rules management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.db.models import ScoringRule
from src.schemas.scoring_rule import ScoringRuleOut, ScoringRuleUpdate

router = APIRouter(prefix="/scoring-rules", tags=["scoring-rules"])


@router.get("", response_model=list[ScoringRuleOut])
@router.get("/", response_model=list[ScoringRuleOut])
async def list_scoring_rules(db: AsyncSession = Depends(get_db)) -> list[ScoringRuleOut]:
    """Return all scoring rules."""
    result = await db.execute(select(ScoringRule).order_by(ScoringRule.id))
    rules = result.scalars().all()
    return [ScoringRuleOut.model_validate(r) for r in rules]


@router.patch("/{rule_id}", response_model=ScoringRuleOut)
async def update_scoring_rule(
    rule_id: int,
    body: ScoringRuleUpdate,
    db: AsyncSession = Depends(get_db),
) -> ScoringRuleOut:
    """Update weight and active for a rule. Weight must be >= 0. Returns updated rule."""
    if body.weight < 0:
        raise HTTPException(status_code=400, detail="weight must be >= 0")
    result = await db.execute(select(ScoringRule).where(ScoringRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Scoring rule not found")
    rule.weight = body.weight
    rule.active = body.active
    await db.commit()
    await db.refresh(rule)
    return ScoringRuleOut.model_validate(rule)
