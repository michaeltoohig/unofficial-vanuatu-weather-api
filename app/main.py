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
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Message
from sqlalchemy import select


from app import models, schemas, templates
from app.config import DEBUG
from app.database import AsyncSession, async_session, get_db_session
from app.forecasts import get_latest_forecasts
from app.locations import LocationDep, get_all_locations
from app.pages import get_latest_page
from app.utils.api import VmgdApiResponse, render_vmgd_api_response
from app.utils.datetime import DateDep


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
                # headers["x-powered-by"] = "microblogpub"
                headers[
                    "referrer-policy"
                ] = "no-referrer, strict-origin-when-cross-origin"
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


app = FastAPI()  # docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

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


@app.get("/")
async def index(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
) -> templates.TemplateResponse:
    query = select(models.Page)
    results = await db_session.execute(query)
    return await templates.render_template(
        db_session,
        request,
        "index.html",
        {
            "pages": results.scalars(),
        },
    )


@app.get("/v1/locations")
async def get_locations(
    requiest: Request,
    db_session: AsyncSession = Depends(get_db_session),
) -> list[schemas.LocationResponse]:
    locations = await get_all_locations(db_session)
    return [
        schemas.LocationResponse(
            id=l.id,
            name=l.name,
            latitude=l.latitude,
            longitude=l.longitude,
        )
        for l in locations
    ]


@app.get("/v1/raw/pages")
async def raw_pages(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
) -> VmgdApiResponse:
    # TODO how to allow user to specify page to return? A PageName enum?
    page = await get_latest_page(db_session)
    data = schemas.RawPageResponse(
        url=page.url,
        data=page.raw_data,
    )
    return render_vmgd_api_response(
        data, issued=page.issued_at, fetched=page.session.fetched_at
    )


@app.get("/v1/forecast")
async def forecast(
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
        schemas.ForecastResponse(
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
    return render_vmgd_api_response(data, issued=issued, fetched=fetched)
