from typing import Annotated

from fastapi import Query, Depends
from fastapi.exceptions import HTTPException
from loguru import logger

from app.scraper.sessions import ForecastSession, WarningSession


async def get_forecast_session_dep(
    session_name: ForecastSession = Query(None, alias="name")
):
    if session_name is None:
        return None
    try:
        session = ForecastSession(session_name)
    except ValueError:
        raise HTTPException(status_code=400, detail="Not a valid scraper session name")
    return session


ScraperSessionDep = Annotated[ForecastSession, Depends(get_forecast_session_dep)]


async def get_warning_session_dep(
    session_name: WarningSession = Query(None, alias="name")
):
    if session_name is None:
        return None
    try:
        session = WarningSession(session_name)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Not a valid weather warning scraper session name"
        )
    return session


WeatherWarningScraperSessionDep = Annotated[
    WarningSession, Depends(get_warning_session_dep)
]
