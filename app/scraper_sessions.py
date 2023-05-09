"""Actions related to the VMGD scraping sessions."""
from http.client import HTTPException
from typing import Annotated

from fastapi import Query, Depends
from sqlalchemy import select
from loguru import logger

from app import models
from app.database import AsyncSession
from app.scraper.sessions import SessionName, WEATHER_WARNING_SESSIONS


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


async def get_warning_weather_session(session_name: str = Query(None, alias="name")):
    if session_name is None:
        return None
    session = SessionName(session_name)
    if not session in WEATHER_WARNING_SESSIONS:
        raise HTTPException(status_code=400, detail="Not a valid weather warning session name")
    return session


WeatherWarningSessionDep = Annotated[SessionName, Depends(get_warning_weather_session)]