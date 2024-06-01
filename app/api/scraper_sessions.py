from typing import Annotated

from fastapi import Query, Depends
from fastapi.exceptions import HTTPException
from loguru import logger

from app.scraper.sessions import SessionName, WEATHER_WARNING_SESSIONS


async def get_scraper_session_dep(session_name: str = Query(None, alias="name")):
    if session_name is None:
        return None
    try:
        session = SessionName(session_name)
    except ValueError:
        raise HTTPException(status_code=400, detail="Not a valid scraper session name")
    return session


ScraperSessionDep = Annotated[SessionName, Depends(get_scraper_session_dep)]


async def get_warning_weather_scraper_session_dep(session: ScraperSessionDep):
    if session not in WEATHER_WARNING_SESSIONS:
        raise HTTPException(
            status_code=400, detail="Not a valid weather warning scraper session name"
        )
    return session


WeatherWarningScraperSessionDep = Annotated[
    SessionName, Depends(get_warning_weather_scraper_session_dep)
]
