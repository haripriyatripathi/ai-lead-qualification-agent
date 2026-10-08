"""Analytics endpoint for dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.schemas.lead import AnalyticsOut
from src.services.lead_service import get_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsOut)
async def analytics(db: AsyncSession = Depends(get_db)) -> AnalyticsOut:
    """Return aggregate analytics: total_leads, high/medium/low_priority counts, average_score."""
    data = await get_analytics(db)
    return AnalyticsOut.model_validate(data)
