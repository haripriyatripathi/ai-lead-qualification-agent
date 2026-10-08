"""Sync database session for Celery worker (no async in worker)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.db.models import Base

# Convert async URL to sync for SQLAlchemy (postgresql+asyncpg -> postgresql+psycopg2)
sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")

sync_engine = create_engine(sync_url, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


def get_sync_session() -> Session:
    """Yield a sync session for use in Celery tasks."""
    return SyncSessionLocal()
