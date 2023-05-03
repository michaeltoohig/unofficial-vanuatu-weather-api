"""Actions related to the VMGD warnings."""
from datetime import datetime
from typing import Annotated
from fastapi import Depends, HTTPException, Query
from sqlalchemy import func, select
from loguru import logger

from app import models
from app.database import AsyncSession, get_db_session
from app.scraper_sessions import get_latest_session

async def get_latest_weather_warning(
    db_session: AsyncSession,
    dt: datetime,
    # category: str | None = None,
) -> models.WeatherWarning | None:
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
        query = (
            select(models.WeatherWarning)
            .where(models.WeatherWarning.session_id == subquery)
        )
    else:
        session = await get_latest_session(db_session)
        query = select(models.WeatherWarning).where(models.WeatherWarning.session_id == session.id)
    ww = (await db_session.execute(query.limit(1))).scalar()
    return ww
