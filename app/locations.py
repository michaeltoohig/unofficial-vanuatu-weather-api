"""Actions related to the VMGD locations."""
from typing import Annotated
from fastapi import Depends, HTTPException, Query
from sqlalchemy import func, select
from loguru import logger

from app import models
from app.database import AsyncSession, get_db_session


async def get_location_dependency(
    db_session: AsyncSession = Depends(get_db_session),
    location_id: int = Query(None, alias="locationId"),
) -> models.Location:
    if location_id is None:
        return None
    location = await get_location_by_id(db_session, location_id)
    if not location:
        raise HTTPException(status_code=400, detail="No location with this ID")
    return location


LocationDep = Annotated[models.Location, Depends(get_location_dependency)]


async def get_all_locations(
    db_session: AsyncSession,
) -> list[models.Location]:
    query = select(models.Location)
    locations = (await db_session.execute(query)).scalars().all()
    return locations


async def get_location_by_id(
    db_session: AsyncSession,
    location_id: int,
) -> models.Location | None:
    query = select(models.Location).where(models.Location.id == location_id)
    location = (await db_session.execute(query)).scalar()
    return location


async def get_location_by_name(
    db_session: AsyncSession,
    name: str,
) -> models.Location | None:
    query = select(models.Location).where(func.lower(models.Location.name) == func.lower(name))
    location = (
        await db_session.execute(
            query.limit(1)
        )
    ).scalar()
    return location


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
        # await db_session.commit()
        await db_session.flush()
        await db_session.refresh(location_object)
    return location_object
