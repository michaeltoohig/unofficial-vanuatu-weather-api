"""Actions related to the VMGD pages."""

from sqlalchemy import select

from loguru import logger

from app import models
from app.database import AsyncSession
from app.scraper_sessions import get_latest_scraper_session


async def get_latest_page(
    db_session: AsyncSession,
    url: str | None = None,
) -> models.Page | None:
    # TODO: currently would fail to find a page if the latest session doesn't corrospond the desired page
    session = await get_latest_scraper_session(db_session)
    query = select(models.Page).where(models.Page.session_id == session.id)
    if url:
        query = query.where(models.Page.url == url)
    page = (await db_session.execute(query.limit(1))).scalar()
    return page
