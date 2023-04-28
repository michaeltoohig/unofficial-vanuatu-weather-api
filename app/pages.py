"""Actions related to the VMGD pages."""
from sqlalchemy import select

from loguru import logger

from app import models
from app.database import AsyncSession


async def get_latest_page(
    db_session: AsyncSession,
    url: str | None,
) -> models.Page | None:
    query = select(models.Page).order_by(models.Page.fetched_at.desc())
    if url:
        query = query.where(models.Page.url == url)
    page = (await db_session.execute(query.limit(1))).scalar()
    return page
