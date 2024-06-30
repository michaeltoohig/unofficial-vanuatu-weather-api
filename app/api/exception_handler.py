from fastapi import Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import templates
from app.api.main import app
from app.database import async_session


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
