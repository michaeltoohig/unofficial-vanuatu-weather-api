"""Actions related to the VMGD weather warnings."""
from datetime import datetime, timedelta
from sqlalchemy import func, select, and_, or_
from sqlalchemy.orm import aliased
from loguru import logger

from app import models
from app.database import AsyncSession
from app.scraper.sessions import WEATHER_WARNING_SESSIONS, SessionName
from app.scraper_sessions import get_latest_session
from app.utils.datetime import now


async def get_latest_weather_warnings(
    db_session: AsyncSession,
    dt: datetime | None = None,
    session_name: SessionName | None = None,
) -> list[models.WeatherWarning] | None:
    subq = (
        select(
            models.WeatherWarning.session_id,
            func.max(models.Session.completed_at).label("max_completed_at")
        )
        .join(models.Session)
        .group_by(models.WeatherWarning.session_id)
        .subquery()
    )

    query = (
        select(models.WeatherWarning)
        .join(models.Session)
        .filter(models.WeatherWarning.session_id == models.Session.id)
        .filter(models.Session.completed_at == subq.c.max_completed_at)
    )

    if session_name is not None:
        query = query.filter(models.Session._name == session_name.value)

    if dt is not None:
        start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        query = (
            select(models.WeatherWarning)
            .join(models.Session)
            .filter(models.WeatherWarning.session_id == models.Session.id)
            # .filter(models.Session._name == session_name.value)
            .filter(and_(models.WeatherWarning.date >= start, models.WeatherWarning.date < end))
            .order_by(models.WeatherWarning.date.desc())
            .limit(1)
            # .group_by(models.Session._name)
        )

    ww = (await db_session.execute(query)).scalars().all()
    return ww


    # subq = (
    #     select(
    #         models.WeatherWarning.session_id,
    #         func.max(models.WeatherWarning.issued_at).label("max_issued_at")
    #     )
    #     .group_by(models.WeatherWarning.session_id)
    #     .subquery()
    # )

    # query = (
    #     select(models.WeatherWarning)
    #     .join(models.Session)
    #     .filter(models.WeatherWarning.session_id == models.Session.id)
    #     # .filter(models.WeatherWarning.issued_at == subq.c.max_issued_at)
    # )

    # if session_name is not None:
    #     query = query.filter(models.Session._name == session_name)

    # if dt is not None:
    #     start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    #     end = start + timedelta(days=1)
    #     query = (
    #         query
    #         .filter(and_(models.WeatherWarning.date >= start, models.WeatherWarning.date < end))
    #     )

    # ww = (await db_session.execute(query)).scalars().all()

    # latest_sessions_subq = (
    #     select(
    #         models.Session._name.label("name"),
    #         func.max(models.Session.completed_at).label("max_completed_at")
    #     )
    #     .where(models.Session.completed_at.isnot(None))
    #     .where(models.Session)
    #     .group_by(models.Session._name)
    #     .subquery()
    # )

    # query = (
    #     select(models.WeatherWarning)
    #     .join(latest_sessions_subq, and_(
    #         models.Session._name == latest_sessions_subq.c.name,
    #         models.Session.completed_at == latest_sessions_subq.c.max_completed_at
    #     ))
    #     .where(and_(
    #         models.Session._name.in_(map(lambda x: x.value, WEATHER_WARNING_SESSIONS))
    #         if not session_name else models.Session._name == session_name.value,
    #         models.WeatherWarning.date == dt
    #     ))
    #     .order_by(models.WeatherWarning.issued_at.desc())
    # )

    # ww = (await db_session.execute(query)).scalars().all()
    # return ww

# async def get_latest_weather_warnings(
#     db_session: AsyncSession,
#     dt: datetime | None = None,
#     session_name: SessionName | None = None,
# ) -> list[models.WeatherWarning] | None:
#     latest_sessions = aliased(models.Session)
#     subq = (
#         select(models.Session._name, func.max(models.Session.completed_at).label("max_completed_at"))
#         .where(models.Session.completed_at is not None)
#         .where(models.Session._name.in_(map(lambda x: x.value, WEATHER_WARNING_SESSIONS) if not session_name else [session_name.value]))
#         .group_by(models.Session._name)
#     )
#     # if dt is None:9.completed_at <= dt)
#     subq = subq.subquery()
#     query = (
#         select(models.WeatherWarning)
#         .join(latest_sessions, models.WeatherWarning.session_id == latest_sessions.id)
#         # .where(models.WeatherWarning.date == dt)
#         .join(
#             subq,
#             (latest_sessions._name == subq.c._name) &
#             (latest_sessions.completed_at == subq.c.max_completed_at)
#         )
#     )
#     ww = (await db_session.execute(query)).scalars().all()
#     return ww

    # if dt:
    #     subquery = (
    #         select(models.Session.id)
    #         .join(models.Session.forecasts)
    #         .filter(models.Session.completed_at is not None)
    #         .filter(models.WeatherWarning.date == dt)
    #         .order_by(models.Session.completed_at.desc())
    #         .limit(1)
    #         .scalar_subquery()
    #     )
    #     query = select(models.WeatherWarning).where(
    #         models.WeatherWarning.session_id == subquery
    #     )
    # else:
    #     session = await get_latest_session(db_session)
    #     query = select(models.WeatherWarning).where(
    #         models.WeatherWarning.session_id == session.id
    #     )
    # ww = (await db_session.execute(query)).scalars().all()
    # return ww
