"""Actions related to the forecasts."""
from datetime import datetime
from sqlalchemy import select

from loguru import logger

from app import models
from app.database import AsyncSession
from app.scraper.sessions import SessionName
from app.scraper_sessions import get_latest_session


async def _get_latest_forecast_session_subquery(
    db_session: AsyncSession,
    location: models.Location,
    dt: datetime,
):
    subquery = (
        select(models.Session.id)
        .join(models.Session.forecasts)
        .filter(models.Session.completed_at is not None)
        .filter(models.ForecastDaily.date == dt)
    )
    if location:
        subquery = subquery.filter(models.ForecastDaily.location_id == location.id)
    return (
        subquery.order_by(models.Session.completed_at.desc()).limit(1).scalar_subquery()
    )


async def get_latest_forecasts(
    db_session: AsyncSession,
    location: models.Location,
    dt: datetime,
) -> models.Page | None:
    query = select(models.ForecastDaily)
    if location:
        query = query.where(models.ForecastDaily.location_id == location.id)
    if dt:
        subq = await _get_latest_forecast_session_subquery(db_session, location, dt)
        query = query.where(models.ForecastDaily.session_id == subq).where(
            models.ForecastDaily.date == dt
        )
    else:
        session = await get_latest_session(db_session)
        query = query.where(models.ForecastDaily.session_id == session.id)
    forecasts = (await db_session.execute(query)).scalars().all()
    return forecasts
