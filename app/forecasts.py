"""Actions related to the forecasts."""
from datetime import date
from sqlalchemy import select

from loguru import logger

from app import models
from app.database import AsyncSession
from app.scraper.sessions import SessionName
from app.scraper_sessions import get_latest_session


async def get_latest_forecast(
    db_session: AsyncSession,
    location_id: int,
    dt: date,
) -> models.Page | None:
    session = await get_latest_session(db_session)
    query = select(models.ForecastDaily).where(models.ForecastDaily.session_id == session.id)
    if location_id:
        query = query.where(models.ForecastDaily.location_id == location_id)
    if dt:
        query = query.where(models.ForecastDaily.date == dt)
    forecasts = (await db_session.execute(query)).scalars().all()
    return forecasts
