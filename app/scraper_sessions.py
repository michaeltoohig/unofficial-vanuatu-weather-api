"""Actions related to the VMGD scraping sessions."""
from datetime import datetime
from typing import Annotated

from fastapi import Query, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from loguru import logger

from app import models
from app.database import AsyncSession
from app.scraper.sessions import SessionName, WEATHER_WARNING_SESSIONS


async def get_latest_scraper_session(
    db_session: AsyncSession,
    *,
    name: SessionName | None = None,
    successful_run_only: bool = False,
    dt: datetime | None = None,
) -> models.Session:
    """Return latest scraper session."""
    query = select(models.Session)
    if name is not None:
        query = query.where(models.Session._name == name.value)
    if successful_run_only:
        query = query.where(models.Session.completed_at is not None)
    if dt:
        query = query.where(models.Session.started_at <= dt)
    query = query.order_by(models.Session.started_at.desc()).limit(1)
    return (await db_session.execute(query)).scalar()


async def get_scraper_session_dep(session_name: str = Query(None, alias="name")):
    if session_name is None:
        return None
    try:
        session = SessionName(session_name)
    except ValueError:
        raise HTTPException(status_code=400, detail="Not a valid scraper session name")
    return session


ScraperSessionDep = Annotated[SessionName, Depends(get_scraper_session_dep)]


async def get_warning_weather_scraper_session_dep(session: ScraperSessionDep):
    if session not in WEATHER_WARNING_SESSIONS:
        raise HTTPException(status_code=400, detail="Not a valid weather warning scraper session name")
    return session


WeatherWarningScraperSessionDep = Annotated[SessionName, Depends(get_warning_weather_scraper_session_dep)]