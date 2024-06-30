import os
import sys
import time

from asgiref.typing import ASGI3Application
from asgiref.typing import ASGIReceiveCallable
from asgiref.typing import ASGISendCallable
from asgiref.typing import Scope
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import Message

from app.config import DEBUG, ROOT_DIR, VMGD_IMAGE_PATH, PROJECT_NAME
from app.api.endpoints import api_router


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
app.include_router(api_router, prefix="/v1")

logger.configure(extra={"request_id": "no_req_id"})
logger.remove()
logger_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{extra[request_id]} - <level>{message}</level>"
)
logger.add(sys.stdout, format=logger_format, level="DEBUG" if DEBUG else "INFO")


@app.get("/", include_in_schema=False)
async def index_page() -> RedirectResponse:
    return RedirectResponse("/docs")  # request.url_for("forecast_page"))


@app.get("/ping", include_in_schema=False)
async def get_healthcheck() -> JSONResponse:
    return JSONResponse(content={"message": "PONG!"})


#
## Basic HTML endpoints that don't look good
#

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
