"""Actions related to the forecast media."""
from datetime import datetime, timedelta
from sqlalchemy import select

from loguru import logger

from app import models
from app.database import AsyncSession
from app.scraper.sessions import SessionName
from app.scraper_sessions import get_latest_session


async def _get_latest_forecast_media_session_subquery(
    db_session: AsyncSession,
    dt: datetime,
):
    # TODO use `start` and `end` date for weather date filters like warnings
    start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    subquery = (
        select(models.Session.id)
        .join(models.Session.media)
        .filter(models.Session.completed_at is not None)
        .filter(models.ForecastMedia.issued_at >= start, models.ForecastMedia.issued_at < end)
        .order_by(models.Session.completed_at.desc())
        .limit(1)
        .scalar_subquery()
    )
    return subquery


async def get_latest_forecast_media(
    db_session: AsyncSession,
    dt: datetime | None = None,
) -> models.Page | None:
    query = select(models.ForecastMedia)
    if dt:
        subq = await _get_latest_forecast_media_session_subquery(db_session, dt)
        query = (
            query.where(models.ForecastMedia.session_id == subq)
            # .where(models.ForecastMedia.date == dt)
        )
    else:
        # XXX possible failure here due to unspecified session name
        session = await get_latest_session(db_session)
        query = query.where(models.ForecastMedia.session_id == session.id)
    forecast_media = (await db_session.execute(query)).scalar()
    return forecast_media


async def get_images_by_session_id(
    db_session: AsyncSession,
    session_id: int,
) -> list[models.Image]:
    query = (
        select(models.Image)
        .where(models.Image.session_id == session_id)
    )
    images = (await db_session.execute(query)).scalars().all()
    return images