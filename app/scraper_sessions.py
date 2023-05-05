"""Actions related to the VMGD scraping sessions."""
from sqlalchemy import select

from loguru import logger

from app import models
from app.database import AsyncSession
from app.scraper.sessions import SessionName


async def get_latest_session(
    db_session: AsyncSession, session_name: SessionName | None = None
) -> models.Session | None:
    """Returns lastest successfully completed scraping session."""
    query = (
        select(models.Session)
        .where(models.Session.completed_at is not None)
        .order_by(models.Session.completed_at.desc())
        .limit(1)
    )
    if session_name:
        query = query.where(models.Session._name == SessionName.value)
    session = (await db_session.execute(query)).scalar()
    return session
