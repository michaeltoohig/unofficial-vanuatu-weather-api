"""Actions related to the VMGD locations."""
from sqlalchemy import func, select
from loguru import logger

from app import models
from app.database import AsyncSession


async def get_location_by_name(
    db_session: AsyncSession,
    name: str | None,
) -> models.Location | None:
    query = select(models.Location).where(func.lower(models.Location.name) == func.lower(name))
    return (
        await db_session.execute(
            query.limit(1)
        )
    ).scalar()


async def save_forecast_location(
    db_session: AsyncSession,
    name: str,
    latitude: float,
    longitude: float,
) -> models.Location:
    location_object = await get_location_by_name(db_session, name)
    if location_object is None:
        location_object = models.Location(name, latitude, longitude)
        db_session.add(location_object)
        await db_session.flush()
        await db_session.refresh(location_object)
    return location_object
