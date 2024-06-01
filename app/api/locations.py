from typing import Annotated
from fastapi import Depends, HTTPException, Query

from app import models
from app.database import AsyncSession, get_db_session
from app.locations import get_location_by_id, get_location_by_slug
from app.utils.slugify import slugify


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


async def get_location_by_slug_dependency(
    db_session: AsyncSession = Depends(get_db_session),
    location_name: str = Query("Port Vila", alias="location"),
) -> models.Location:
    slug = slugify(location_name)
    location = await get_location_by_slug(db_session, slug)
    if not location:
        raise HTTPException(status_code=404, detail="No location with this name")
    return location


LocationSlugDep = Annotated[models.Location, Depends(get_location_by_slug_dependency)]
