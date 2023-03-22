from fastapi import Depends, FastAPI, Request

from app import config
from app.database import AsyncSession, get_db_session



# class CustomMiddleware:
#     """Raw ASGI middleware as using starlette base middleware causes issues
#     with both:
#      - Jinja2: https://github.com/encode/starlette/issues/472
#      - async SQLAchemy: https://github.com/tiangolo/fastapi/issues/4719
#     """

#     def __init__(
#         self,
#         app: ASGI3Application,
#     ) -> None:
#         self.app = app

#     async def __call__(
#         self, scope: Scope, receive: ASGIReceiveCallable, send: ASGISendCallable
#     ) -> None:
#         # We only care about HTTP requests
#         if scope["type"] != "http":
#             await self.app(scope, receive, send)
#             return

#         response_details = {"status_code": None}
#         start_time = time.perf_counter()
#         request_id = os.urandom(8).hex()

#         async def send_wrapper(message: Message) -> None:
#             if message["type"] == "http.response.start":

#                 # Extract the HTTP response status code
#                 response_details["status_code"] = message["status"]

#                 # And add the security headers
#                 headers = MutableHeaders(scope=message)
#                 headers["X-Request-ID"] = request_id
#                 headers["x-powered-by"] = "microblogpub"
#                 headers[
#                     "referrer-policy"
#                 ] = "no-referrer, strict-origin-when-cross-origin"
#                 headers["x-content-type-options"] = "nosniff"
#                 headers["x-xss-protection"] = "1; mode=block"
#                 headers["x-frame-options"] = "DENY"
#                 headers["permissions-policy"] = "interest-cohort=()"
#                 headers["content-security-policy"] = (
#                     (
#                         f"default-src 'self'; "
#                         f"style-src 'self' 'sha256-{HIGHLIGHT_CSS_HASH}'; "
#                         f"frame-ancestors 'none'; base-uri 'self'; form-action 'self';"
#                     )
#                     if not config.CUSTOM_CONTENT_SECURITY_POLICY
#                     else config.CUSTOM_CONTENT_SECURITY_POLICY.format(
#                         HIGHLIGHT_CSS_HASH=HIGHLIGHT_CSS_HASH
#                     )
#                 )
#                 if not DEBUG:
#                     headers["strict-transport-security"] = "max-age=63072000;"

#             await send(message)  # type: ignore

#         # Make loguru ouput the request ID on every log statement within
#         # the request
#         with logger.contextualize(request_id=request_id):
#             client_host, client_port = scope["client"]  # type: ignore
#             scheme = scope["scheme"]
#             server_host, server_port = scope["server"]  # type: ignore
#             request_method = scope["method"]
#             request_path = scope["path"]
#             headers = Headers(raw=scope["headers"])  # type: ignore
#             user_agent = headers.get("user-agent")
#             logger.info(
#                 f"{client_host}:{client_port} - "
#                 f"{request_method} "
#                 f"{scheme}://{server_host}:{server_port}{request_path} - "
#                 f'"{user_agent}"'
#             )
#             try:
#                 await self.app(scope, receive, send_wrapper)  # type: ignore
#             finally:
#                 elapsed_time = time.perf_counter() - start_time
#                 logger.info(
#                     f"status_code={response_details['status_code']} "
#                     f"{elapsed_time=:.2f}s"
#                 )

#         return None


app = FastAPI(
    docs_url=None, redoc_url=None, dependencies=[Depends(_check_0rtt_early_data)]
)

# app.add_middleware(CustomMiddleware)

@app.get("/remote_follow")
async def get_remote_follow(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
) -> templates.TemplateResponse:
    return await templates.render_template(
        db_session,
        request,
        "remote_follow.html",
        {},
    )
