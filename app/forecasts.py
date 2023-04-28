"""Actions related to the forecasts."""
from sqlalchemy import select

from loguru import logger

from app import models
from app.database import AsyncSession
from app.scraper.sessions import SessionName


async def get_latest_forecast(
    db_session: AsyncSession,
    location_id: int,
) -> models.Page | None:
    query = (
        select(models.Session)
        .where(models.Session.completed_at is not None)
        .where(models.Session._name == SessionName.GENERAL_FORECAST.value)
        .order_by(models.Session.completed_at.desc())
        .limit(1)
    )
    session = (await db_session.execute(query)).scalar()

    query = select(models.ForecastDaily).where(models.ForecastDaily.session_id == session.id)
    if location_id:
        query = query.where(models.ForecastDaily.location_id == location_id)
    forecasts = (await db_session.execute(query)).scalars()
    return forecasts
