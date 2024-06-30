from datetime import datetime, timedelta
from itertools import chain
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse as TemplateResponse

from app import config
from app.config import DEBUG, PROJECT_REPO, VERSION, PROJECT_NAME
from app.database import AsyncSession
from app.scraper.sessions import ForecastSession, WarningSession
from app.scraper_sessions import get_latest_scraper_session
from app.utils.datetime import as_vu, now


_templates = Jinja2Templates(
    directory=["app/api/templates"],  # type: ignore  # bad typing
    trim_blocks=True,
    lstrip_blocks=True,
)


def forecast_date(value: datetime):
    if value.date() == now().date():
        return "Today"
    elif value.date() == now().date() + timedelta(days=1):
        return "Tomorrow"
    else:
        return value.strftime("%A, %d %B")


def degrees(value: str):
    """Returns given temperature value as HTML ready string with superscript degrees C."""
    # alternative to "°" is "℃"
    value = int(
        value
    )  # sanity check to be sure we only get integers since I don't want to call `safe` on the results of this if strings are passed
    return f"{value}<small><sup>℃</sup></small>"


def vu_datetime_str(value):
    dt = as_vu(value)
    return dt.strftime("%Y %b %d %H:%M %p (UTC+11)")


_templates.env.filters["forecast_date"] = forecast_date
_templates.env.filters["degrees"] = degrees
_templates.env.filters["vanuatu_time"] = as_vu
_templates.env.filters["vu_datetime"] = vu_datetime_str


async def render_template(
    db_session: AsyncSession,
    request: Request,
    template: str,
    template_args: dict[str, Any] | None = None,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> TemplateResponse:
    if template_args is None:
        template_args = {}

    scraper_sessions = []
    for session_name in chain(ForecastSession, WarningSession):
        session = await get_latest_scraper_session(
            db_session, session_name=session_name
        )
        scraper_sessions.append(session)

    github_icon = request.url_for("static", path="github.svg")

    return _templates.TemplateResponse(
        template,
        {
            "request": request,
            "debug": DEBUG,
            "project_version": VERSION,
            "project_name": PROJECT_NAME,
            "project_repo": PROJECT_REPO,
            "github_icon": github_icon,
            # "csrf_token": generate_csrf_token(),
            # "highlight_css": HIGHLIGHT_CSS,
            # "notifications_count": await db_session.scalar(
            #     select(func.count(models.Notification.id)).where(
            #         models.Notification.is_new.is_(True)
            #     )
            # )
            # if is_admin
            # else 0,
            # "articles_count": await db_session.scalar(
            #     select(func.count(models.OutboxObject.id)).where(
            #         models.OutboxObject.visibility == ap.VisibilityEnum.PUBLIC,
            #         models.OutboxObject.is_deleted.is_(False),
            #         models.OutboxObject.is_hidden_from_homepage.is_(False),
            #         models.OutboxObject.ap_type == "Article",
            #     )
            # ),
            # "followers_count": await db_session.scalar(
            #     select(func.count(models.Follower.id))
            # ),
            # "following_count": await db_session.scalar(
            #     select(func.count(models.Following.id))
            # ),
            # "actor_types": ap.ACTOR_TYPES,
            # "custom_footer": CUSTOM_FOOTER,
            "scraper_sessions": scraper_sessions,
            **template_args,
        },
        status_code=status_code,
        headers=headers,
    )


_templates.env.globals["CSS_HASH"] = config.CSS_HASH
_templates.env.globals["BASE_URL"] = config.BASE_URL
