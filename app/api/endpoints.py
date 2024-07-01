from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from app.api.locations import LocationDep
from app.api import responses
from app.api.scraper_sessions import (
    ScraperSessionDep,
    WeatherWarningScraperSessionDep,
)
from app.database import AsyncSession, get_db_session
from app.forecast_media import get_images_by_session_id, get_latest_forecast_media
from app.forecasts import get_latest_forecasts
from app.locations import get_all_locations

from app.scraper.sessions import WarningSession

from app.scraper_sessions import get_latest_scraper_session
from app.api.responses import (
    VmgdApiForecastResponse,
    VmgdApiForecastMediaResponse,
    VmgdApiWeatherWarningResponse,
    VmgdApiWeatherWarningsResponse,
)
from app.api.utils import render_vmgd_api_response
from app.utils.datetime import DateDep, now
from app.weather_warnings import get_latest_weather_warning

api_router = APIRouter()


@api_router.get("/locations")
async def get_locations(
    db_session: AsyncSession = Depends(get_db_session),
) -> list[responses.LocationResponseData]:
    locations = await get_all_locations(db_session)
    return [
        responses.LocationResponseData(
            id=location.id,
            name=location.name,
            latitude=location.latitude,
            longitude=location.longitude,
        )
        for location in locations
    ]


@api_router.get("/forecasts")
async def get_forecasts(
    db_session: AsyncSession = Depends(get_db_session),
    *,
    location: LocationDep,
    dt: DateDep,
) -> VmgdApiForecastResponse:
    forecasts = await get_latest_forecasts(db_session, location, dt)
    if not forecasts:
        raise HTTPException(status_code=404, detail="No forecast data available")
    data = [
        responses.ForecastResponseData(
            location=forecast.location.id,
            date=forecast.date,
            summary=forecast.summary,
            minTemp=forecast.minTemp,
            maxTemp=forecast.maxTemp,
            minHumi=forecast.minHumi,
            maxHumi=forecast.maxHumi,
        )
        for forecast in forecasts
    ]
    issued = forecasts[0].issued_at
    fetched = forecasts[0].session.fetched_at
    return await render_vmgd_api_response(
        data,
        response_class=VmgdApiForecastResponse,
        issued=issued,
        fetched=fetched,
    )


@api_router.get("/media")
async def get_forecast_media_(
    db_session: AsyncSession = Depends(get_db_session),
    *,
    dt: DateDep,
) -> VmgdApiForecastMediaResponse:
    if dt is None:
        dt = now()
    forecast_media = await get_latest_forecast_media(db_session, dt)
    if not forecast_media:
        raise HTTPException(status_code=404, detail="No forecast data available")

    images = await get_images_by_session_id(db_session, forecast_media.session_id)
    data = responses.ForecastMediaResponseData(
        summary=forecast_media.summary,
        images=[img._server_filepath for img in images] if images is not None else [],
    )
    issued = forecast_media.issued_at
    fetched = forecast_media.session.fetched_at
    return await render_vmgd_api_response(
        data,
        response_class=VmgdApiForecastMediaResponse,
        issued=issued,
        fetched=fetched,
    )


@api_router.get("/warnings")
async def get_weather_warnings_(
    db_session: AsyncSession = Depends(get_db_session),
    *,
    dt: DateDep,
) -> VmgdApiWeatherWarningsResponse:
    if not dt:
        dt = now()
    weather_warnings = []
    for session_name in WarningSession:
        ww = await get_latest_weather_warning(
            db_session, dt=dt, session_name=session_name
        )
        if ww:
            weather_warnings.append(ww)

    if not weather_warnings:
        raise HTTPException(status_code=404, detail="No weather warning data available")
    data = [
        responses.WeatherWarningResponseData(
            date=w.date,
            name=w.session._name,
            body=w.body,
        )
        for w in weather_warnings
    ]
    issued = min(map(lambda w: w.issued_at, weather_warnings))
    fetched = min(map(lambda w: w.session.fetched_at, weather_warnings))
    return await render_vmgd_api_response(
        data,
        response_class=VmgdApiWeatherWarningsResponse,
        issued=issued,
        fetched=fetched,
    )


@api_router.get("/warnings/{warning_name}")
async def get_weather_warning(
    db_session: AsyncSession = Depends(get_db_session),
    *,
    warning_name: WarningSession,
    dt: DateDep,
) -> VmgdApiWeatherWarningResponse:
    if not dt:
        dt = now()
    ww = await get_latest_weather_warning(
        db_session,
        dt=dt,
        session_name=warning_name,
    )
    if not ww:
        raise HTTPException(
            status_code=404, detail="No weather warnings data available"
        )
    data = responses.WeatherWarningResponseData(
        date=ww.date,
        name=ww.session._name,
        body=ww.body,
    )
    return await render_vmgd_api_response(
        data,
        response_class=VmgdApiWeatherWarningResponse,
        issued=ww.issued_at,
        fetched=ww.session.fetched_at,
    )


#
# TODO: reintroduce to API
#
# @api_router.get("/raw/sessions")
# async def get_raw_sessions(
#     request: Request,
#     db_session: AsyncSession = Depends(get_db_session),
#     *,
#     name: ScraperSessionDep,
# ) -> JSONResponse:
#     """Returns raw results from a scraper session.
#     Useful to track the success/failure status of each session which we display on our home page.
#     Can help see if our data is up-to-date or if the source material may have changed its format.
#     """
#     # TODO accept `date` query parameter to allow user to select date of sessions' status for historical purposes
#     if name:
#         session = await get_latest_scraper_session(db_session, name=name)
#         return responses.RawSessionResponse(
#             name=name,
#             success=session.completed_at is not None,
#             started_at=session.started_at,
#         )
#     else:
#         scraper_sessions = []
#         for name in SessionName:
#             session = await get_latest_scraper_session(db_session, name=name)
#             if session is None:
#                 scraper_sessions.append(
#                     responses.RawSessionResponse(
#                         name=name.value,
#                         success=False,
#                         started_at=None,
#                     )
#                 )
#             else:
#                 scraper_sessions.append(
#                     responses.RawSessionResponse(
#                         name=name.value,
#                         success=session.completed_at is not None,
#                         started_at=session.started_at,
#                     )
#                 )
#         return scraper_sessions
#

#
# TODO: reintroduce to API
#
# @api_router.get("/raw/pages")
# async def get_raw_pages(
#     request: Request,
#     db_session: AsyncSession = Depends(get_db_session),
# ) -> VmgdApiResponse:
#     """Returns the raw results from a single scraped page.
#     Useful for historical purposes and/or verifying our results.
#     """
#     # TODO allow user to add `date` query parameter to view old page data
#     # TODO how to allow user to specify page to return? A PageName enum? Or use session enum?
#     page = await get_latest_page(db_session)
#     data = responses.RawPageResponse(
#         url=page._path,
#         data=page.raw_data,
#     )
#     return await render_vmgd_api_response(
#         db_session,
#         request,
#         data,
#         issued=page.issued_at,
#         fetched=page.session.fetched_at,
#     )
