"""FastAPI dependencies."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_async_session

# Re-export for route use
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield async DB session."""
    async for session in get_async_session():
        yield session
