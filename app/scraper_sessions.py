"""Actions related to the VMGD scraping sessions."""

from datetime import datetime

from sqlalchemy import select
from loguru import logger

from app import models
from app.database import AsyncSession

from app.scraper.sessions import ForecastSession, WarningSession


async def get_latest_scraper_session(
    db_session: AsyncSession,
    *,
    session_name: ForecastSession | WarningSession | None = None,
    successful_run_only: bool = False,
    dt: datetime | None = None,
) -> models.Session:
    """Return latest scraper session."""
    query = select(models.Session)
    if session_name is not None:
        query = query.where(models.Session._name == session_name.value)
    if successful_run_only:
        query = query.where(models.Session.completed_at is not None)
    if dt:
        query = query.where(models.Session.started_at <= dt)
    query = query.order_by(models.Session.started_at.desc()).limit(1)
    return (await db_session.execute(query)).scalar()
