from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse as TemplateResponse

from app import config
from app.config import DEBUG, VERSION
from app.database import AsyncSession


_templates = Jinja2Templates(
    directory=["app/templates"],  # type: ignore  # bad typing
    trim_blocks=True,
    lstrip_blocks=True,
)


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

    return _templates.TemplateResponse(
        template,
        {
            "request": request,
            "debug": DEBUG,
            "project_version": VERSION,
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
            **template_args,
        },
        status_code=status_code,
        headers=headers,
    )


_templates.env.globals["CSS_HASH"] = config.CSS_HASH
_templates.env.globals["BASE_URL"] = config.BASE_URL
