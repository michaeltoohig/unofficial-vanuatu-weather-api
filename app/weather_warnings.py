"""Actions related to the VMGD weather warnings."""
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.orm import aliased
from loguru import logger

from app import models
from app.database import AsyncSession
from app.scraper.sessions import WEATHER_WARNING_SESSIONS, SessionName
from app.scraper_sessions import get_latest_session


async def get_latest_weather_warnings(
    db_session: AsyncSession,
    dt: datetime,
    session_name: SessionName | None = None,
) -> models.WeatherWarning | None:
    latest_sessions = aliased(models.Session)
    subq = (
        select(models.Session._name, func.max(models.Session.completed_at).label("max_completed_at"))
        .where(models.Session._name.in_(map(lambda x: x.value, WEATHER_WARNING_SESSIONS) if not session_name else [session_name.value]))
        .group_by(models.Session._name)
        .subquery()
    )
    query = (
        select(models.WeatherWarning)
        .join(latest_sessions, models.WeatherWarning.session_id == latest_sessions.id)
        .join(
            subq,
            (latest_sessions._name == subq.c._name) &
            (latest_sessions.completed_at == subq.c.max_completed_at)
        )
    )
    ww = (await db_session.execute(query)).scalars().all()
    return ww

    if dt:
        subquery = (
            select(models.Session.id)
            .join(models.Session.forecasts)
            .filter(models.Session.completed_at is not None)
            .filter(models.WeatherWarning.date == dt)
            .order_by(models.Session.completed_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        query = select(models.WeatherWarning).where(
            models.WeatherWarning.session_id == subquery
        )
    else:
        session = await get_latest_session(db_session)
        query = select(models.WeatherWarning).where(
            models.WeatherWarning.session_id == session.id
        )
    ww = (await db_session.execute(query)).scalars().all()
    return ww
