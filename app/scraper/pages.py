from dataclasses import dataclass
import enum
import hashlib
import json
from sqlalchemy import select

from loguru import logger

from app import config, models
from app.database import AsyncSession
from app.utils.datetime import now
from app.scraper.utils import _save_html


class PagePath(enum.Enum):
    FORECAST_MAP = "/forecast-division"
    FORECAST_WEEK = "/forecast-division/public-forecast/7-day"
    FORECAST_MEDIA = "/forecast-division/public-forecast/media"
    WARNING_BULLETIN = "/forecast-division/warnings/current-bulletin"
    WARNING_MARINE = "/forecast-division/warnings/marine-warning"
    WARNING_HIGHT_SEAS = "/forecast-division/warnings/hight-seas-warning"
    WARNING_SEVERE_WEATHER = "/forecast-division/warnings/severe-weather-warning"


@dataclass
class PageMapping:
    path: PagePath
    process: callable
    scraper: callable = None
    # process_images: callable | None  # TODO decide how to handle pages that have images.

    @property
    def url(self):
        return config.VMGD_BASE_URL + self.path.value

    @property
    def slug(self):
        return self.path.value.rsplit("/", 1)[1]


async def handle_page_error(
    db_session: AsyncSession,
    url: str,
    description: str,
    exc: str,
    html,
    raw_data,
    errors,
) -> models.PageError | None:
    """make page error or increment counter on existing error"""
    logger.warning(f"Page error {description} for {url}")
    if html is not None:
        html_hash = hashlib.md5(html.encode("utf-8")).hexdigest()
    else:
        html_hash = None

    query = select(models.PageError).where(
        models.PageError.url == url,
        models.PageError._description == description,
        models.PageError.exception == exc,
    )
    if html_hash is not None:
        json_str_raw_data = json.dumps(raw_data) if raw_data is not None else None
        json_str_errors = json.dumps(errors) if errors is not None else None
        query = query.where(
            models.PageError.html_hash == html_hash,
            models.PageError._raw_data == json_str_raw_data,
            models.PageError._errors == json_str_errors,
        )
    result = await db_session.execute(query.limit(1))
    existing = result.scalars().one_or_none()
    if existing:
        existing.count += 1
        existing.updated_at = now()
        db_session.add(existing)
        await db_session.commit()
    else:
        if html_hash is not None:
            fp = models.PageError.get_html_directory() / html_hash
            _save_html(html, fp)
        page_error = models.PageError(
            url=url,
            description=description,
            exception=exc,
            html_hash=html_hash,
            raw_data=raw_data,
            errors=errors,
        )
        db_session.add(page_error)
        await db_session.commit()
