"""Health check routes."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health() -> dict:
    """Basic liveness."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness: DB (and optionally Redis) check."""
    checks: dict[str, str] = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.exception("DB health check failed")
        checks["database"] = str(e)

    return {"status": "ok" if all(v == "ok" for v in checks.values()) else "degraded", "checks": checks}
