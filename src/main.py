"""FastAPI application entrypoint."""
import logging

from contextlib import asynccontextmanager
from sqlalchemy import func, select

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import analytics, health, leads, scoring_rules
from src.db.models import ScoringRule
from src.db.session import async_session_factory
from src.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

DEFAULT_SCORING_RULES = [
    ("role_level", "VP", 20),
    ("role_level", "C-Level", 20),
    ("urgency_level", "High", 15),
    ("company_size", "51-200", 10),
    ("company_size", "201+", 10),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan: startup/shutdown."""
    logger.info("Starting lead qualification API")

    async with async_session_factory() as session:
        try:
            result = await session.execute(select(func.count()).select_from(ScoringRule))
            count = result.scalar() or 0
            if count == 0:
                for rule_type, rule_value, weight in DEFAULT_SCORING_RULES:
                    session.add(
                        ScoringRule(rule_type=rule_type, rule_value=rule_value, weight=weight)
                    )
                await session.commit()
                logger.info("Default scoring rules seeded")
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    yield
    logger.info("Shutting down")


app = FastAPI(title="Lead Qualification API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow dashboard + lead-capture on any localhost port
    allow_credentials=False,  # must be False when allow_origins is "*"
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(health.router)
app.include_router(scoring_rules.router)
app.include_router(leads.router)
app.include_router(analytics.router)
