"""Actions related to the VMGD weather warnings."""

from datetime import datetime, timedelta
from sqlalchemy import select
from loguru import logger

from app import models
from app.database import AsyncSession
from app.scraper.sessions import WarningSession


async def _get_latest_weather_warning_session_subquery(
    session_name: WarningSession,
    dt: datetime | None,
):
    subquery = (
        select(models.Session.id)
        .join(models.Session.weather_warnings)
        .filter(models.Session.completed_at is not None)
        .filter(models.Session._name == session_name.value)
    )
    if dt:
        start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        subquery = subquery.filter(
            models.WeatherWarning.date >= start, models.WeatherWarning.date < end
        )
    return (
        subquery.order_by(models.Session.completed_at.desc()).limit(1).scalar_subquery()
    )


async def get_latest_weather_warning(
    db_session: AsyncSession,
    session_name: WarningSession,
    dt: datetime | None = None,
) -> models.WeatherWarning | None:
    subquery = await _get_latest_weather_warning_session_subquery(session_name, dt)
    query = select(models.WeatherWarning).where(
        models.WeatherWarning.session_id == subquery
    )
    if dt:
        start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        query = query.where(
            models.WeatherWarning.date >= start, models.WeatherWarning.date < end
        )
    ww = (await db_session.execute(query)).scalars().first()
    return ww
