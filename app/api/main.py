import os
import sys
import time

from asgiref.typing import ASGI3Application
from asgiref.typing import ASGIReceiveCallable
from asgiref.typing import ASGISendCallable
from asgiref.typing import Scope
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Message

from app.api import responses, templates
from app.api.locations import (
    LocationDep,
    LocationSlugDep,
)
from app.api.scraper_sessions import (
    ScraperSessionDep,
    WeatherWarningScraperSessionDep,
)
from app.config import DEBUG, ROOT_DIR, VMGD_IMAGE_PATH, PROJECT_NAME
from app.database import AsyncSession, async_session, get_db_session
from app.forecast_media import get_images_by_session_id, get_latest_forecast_media
from app.forecasts import get_latest_forecasts
from app.locations import (
    get_all_locations,
    get_location_by_name,
)
from app.pages import get_latest_page
from app.scraper.sessions import WEATHER_WARNING_SESSIONS, SessionName
from app.scraper_sessions import (
    get_latest_scraper_session,
)
from app.api.utils import VmgdApiResponse, render_vmgd_api_response
from app.utils.datetime import DateDep, now
from app.weather_warnings import get_latest_weather_warnings


class CustomMiddleware:
    """Raw ASGI middleware as using starlette base middleware causes issues
    with both:
     - Jinja2: https://github.com/encode/starlette/issues/472
     - async SQLAchemy: https://github.com/tiangolo/fastapi/issues/4719
    """

    def __init__(
        self,
        app: ASGI3Application,
    ) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
    ) -> None:
        # We only care about HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_details = {"status_code": None}
        start_time = time.perf_counter()
        request_id = os.urandom(8).hex()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                # Extract the HTTP response status code
                response_details["status_code"] = message["status"]

                # And add the security headers
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["referrer-policy"] = (
                    "no-referrer, strict-origin-when-cross-origin"
                )
                headers["x-content-type-options"] = "nosniff"
                headers["x-xss-protection"] = "1; mode=block"
                headers["x-frame-options"] = "DENY"
                headers["permissions-policy"] = "interest-cohort=()"
                # headers["content-security-policy"] = (
                #     (
                #         f"default-src 'self'; "
                #         f"style-src 'self' 'sha256-{HIGHLIGHT_CSS_HASH}'; "
                #         f"frame-ancestors 'none'; base-uri 'self'; form-action 'self';"
                #     )
                #     if not config.CUSTOM_CONTENT_SECURITY_POLICY
                #     else config.CUSTOM_CONTENT_SECURITY_POLICY.format(
                #         HIGHLIGHT_CSS_HASH=HIGHLIGHT_CSS_HASH
                #     )
                # )
                if not DEBUG:
                    headers["strict-transport-security"] = "max-age=63072000;"

            await send(message)  # type: ignore

        # Make loguru ouput the request ID on every log statement within
        # the request
        with logger.contextualize(request_id=request_id):
            client_host, client_port = scope["client"]  # type: ignore
            scheme = scope["scheme"]
            server_host, server_port = scope["server"]  # type: ignore
            request_method = scope["method"]
            request_path = scope["path"]
            headers = Headers(raw=scope["headers"])  # type: ignore
            user_agent = headers.get("user-agent")
            logger.info(
                f"{client_host}:{client_port} - "
                f"{request_method} "
                f"{scheme}://{server_host}:{server_port}{request_path} - "
                f'"{user_agent}"'
            )
            try:
                await self.app(scope, receive, send_wrapper)  # type: ignore
            finally:
                elapsed_time = time.perf_counter() - start_time
                logger.info(
                    f"status_code={response_details['status_code']} "
                    f"{elapsed_time=:.2f}s"
                )

        return None


app = FastAPI(title=PROJECT_NAME)  # docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="app/api/static"), name="static")
app.mount(
    "/images",
    StaticFiles(directory=str(VMGD_IMAGE_PATH.relative_to(ROOT_DIR))),
    name="images",
)

app.add_middleware(CustomMiddleware)


logger.configure(extra={"request_id": "no_req_id"})
logger.remove()
logger_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{extra[request_id]} - <level>{message}</level>"
)
logger.add(sys.stdout, format=logger_format, level="DEBUG" if DEBUG else "INFO")


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> templates.TemplateResponse | JSONResponse:
    accept_value = request.headers.get("accept")
    if (
        accept_value
        and accept_value.startswith("text/html")
        and not request.url.path.startswith(
            "/v1"
        )  # return JSON response for API requests
        and 400 <= exc.status_code < 600
    ):
        async with async_session() as db_session:
            title = (
                {
                    404: "Oops, nothing to see here",
                    500: "Oops, something went wrong",
                }
            ).get(exc.status_code, exc.detail)
            try:
                return await templates.render_template(
                    db_session,
                    request,
                    "error.html",
                    {"title": title},
                    status_code=exc.status_code,
                )
            finally:
                await db_session.close()
    return await http_exception_handler(request, exc)


@app.get("/", include_in_schema=False)
async def index_page(
    request: Request,
) -> RedirectResponse:
    return RedirectResponse("/docs")  # request.url_for("forecast_page"))


# @app.get("/forecast", include_in_schema=False)
# async def forecast_page(
#     request: Request,
#     db_session: AsyncSession = Depends(get_db_session),
#     *,
#     location: LocationSlugDep,
# ) -> templates.TemplateResponse:
#     if not location:
#         location = await get_location_by_name(
#             db_session, name="Port Vila"
#         )  # default value
#     forecasts = await get_latest_forecasts(db_session, location=location, dt=now())
#     return await templates.render_template(
#         db_session,
#         request,
#         "index.html",
#         {
#             "forecasts": forecasts,
#         },
#     )


# @app.get("/about", include_in_schema=False)
# async def about_page(
#     request: Request,
#     db_session: AsyncSession = Depends(get_db_session),
# ) -> templates.TemplateResponse:
#     # TODO return about page, explain reason for website, roadmap, etc.
#     raise NotImplementedError


@app.get("/ping", include_in_schema=False)
async def get_healthcheck(
    request: Request,
) -> JSONResponse:
    return JSONResponse(content={"message": "PONG!"})


@app.get("/v1/locations")
async def get_locations(
    requiest: Request,
    db_session: AsyncSession = Depends(get_db_session),
) -> list[responses.LocationResponse]:
    locations = await get_all_locations(db_session)
    return [
        responses.LocationResponse(
            id=l.id,
            name=l.name,
            latitude=l.latitude,
            longitude=l.longitude,
        )
        for l in locations
    ]


@app.get("/v1/pages", include_in_schema=False)
async def get_raw_pages(
    request: Request,
):
    # TODO return list of PageMapping objects we scrape
    pass


@app.get("/v1/forecast")
async def get_forecasts(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
    *,
    location: LocationDep,
    dt: DateDep,
) -> VmgdApiResponse:
    forecasts = await get_latest_forecasts(db_session, location, dt)
    if not forecasts:
        raise HTTPException(status_code=404, detail="No forecast data available")
    data = [
        responses.ForecastResponse(
            location=f.location.id,
            date=f.date,
            summary=f.summary,
            minTemp=f.minTemp,
            maxTemp=f.maxTemp,
            minHumi=f.minHumi,
            maxHumi=f.maxHumi,
        )
        for f in forecasts
    ]
    issued = forecasts[0].issued_at
    fetched = forecasts[0].session.fetched_at
    return await render_vmgd_api_response(
        db_session,
        request,
        data,
        issued=issued,
        fetched=fetched,
    )


@app.get("/v1/media")
async def get_forecast_media_(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
    *,
    dt: DateDep,
) -> VmgdApiResponse:
    if dt is None:
        dt = now()
    forecast_media = await get_latest_forecast_media(db_session, dt)
    if not forecast_media:
        raise HTTPException(status_code=404, detail="No forecast data available")

    images = await get_images_by_session_id(db_session, forecast_media.session_id)
    data = responses.ForecastMediaResponse(
        summary=forecast_media.summary,
        images=[img._server_filepath for img in images] if images is not None else [],
    )
    issued = forecast_media.issued_at
    fetched = forecast_media.session.fetched_at
    return await render_vmgd_api_response(
        db_session,
        request,
        data,
        issued=issued,
        fetched=fetched,
    )


@app.get("/v1/warnings")
async def get_weather_warnings_(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
    *,
    dt: DateDep,
    session_name: WeatherWarningScraperSessionDep,
) -> VmgdApiResponse:
    if not dt:
        dt = now()
    weather_warnings = []
    if not session_name:
        for session_name in WEATHER_WARNING_SESSIONS:
            ww = await get_latest_weather_warnings(
                db_session, dt=dt, session_name=session_name
            )
            weather_warnings.extend(ww)
    else:
        ww = await get_latest_weather_warnings(
            db_session, dt=dt, session_name=session_name
        )
        weather_warnings.extend(ww)

    if not weather_warnings:
        raise HTTPException(status_code=404, detail="No weather warning data available")
    data = [
        responses.WeatherWarningResponse(
            date=w.date,
            name=w.session._name,
            body=w.body,
        )
        for w in weather_warnings
    ]
    issued = min(map(lambda w: w.issued_at, weather_warnings))
    fetched = min(map(lambda w: w.session.fetched_at, weather_warnings))
    return await render_vmgd_api_response(
        db_session,
        request,
        data,
        issued=issued,
        fetched=fetched,
        skip_warnings=True,
    )


@app.get("/v1/raw/sessions")
async def get_raw_sessions(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
    *,
    name: ScraperSessionDep,
) -> JSONResponse:
    """Returns raw results from a scraper session.
    Useful to track the success/failure status of each session which we display on our home page.
    Can help see if our data is up-to-date or if the source material may have changed its format.
    """
    # TODO accept `date` query parameter to allow user to select date of sessions' status for historical purposes
    if name:
        session = await get_latest_scraper_session(db_session, name=name)
        return responses.RawSessionResponse(
            name=name,
            success=session.completed_at is not None,
            started_at=session.started_at,
        )
    else:
        scraper_sessions = []
        for name in SessionName:
            session = await get_latest_scraper_session(db_session, name=name)
            if session is None:
                scraper_sessions.append(
                    responses.RawSessionResponse(
                        name=name.value,
                        success=False,
                        started_at=None,
                    )
                )
            else:
                scraper_sessions.append(
                    responses.RawSessionResponse(
                        name=name.value,
                        success=session.completed_at is not None,
                        started_at=session.started_at,
                    )
                )
        return scraper_sessions


@app.get("/v1/raw/pages")
async def get_raw_pages(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
) -> VmgdApiResponse:
    """Returns the raw results from a single scraped page.
    Useful for historical purposes and/or verifying our results.
    """
    # TODO allow user to add `date` query parameter to view old page data
    # TODO how to allow user to specify page to return? A PageName enum? Or use SessionName enum?
    page = await get_latest_page(db_session)
    data = responses.RawPageResponse(
        url=page._path,
        data=page.raw_data,
    )
    return await render_vmgd_api_response(
        db_session,
        request,
        data,
        issued=page.issued_at,
        fetched=page.session.fetched_at,
    )
