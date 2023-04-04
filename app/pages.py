"""Actions related to the VMGD pages."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from sqlalchemy import select

from loguru import logger

from app import config, models
from app.database import AsyncSession
from app.utils.datetime import now


def process_issued_at(
    text: str, delimiter_start: str, delimiter_end: str = "(utc time"
) -> datetime:
    """Given a text containing the `issued_at` value found between two delimiters extract the value and convert to a datetime.
    The general date format appears to be "%a %dXX %B, %Y at %H:%M" where `%dXX` is an ordinal number.
    Examples:
     - "Mon 27th March, 2023 at 15:02 (UTC Time:04:02)"
     - "Tue 28th March, 2023 at 16:05 (UTC Time:05:05)"

    So far I noticed the format of the date appears consistent across pages but the delimiter for the start of the date is inconsistent.
    """
    issued_date_str = (
        text.lower()
        .split(delimiter_start.lower(), 1)[1]
        .split(delimiter_end.lower())[0]
        .strip()
    )
    issued_date_str = (
        issued_date_str[:6] + issued_date_str[8:]
    )  # remove 'st', 'nd', 'rd', 'th'
    issued_at = datetime.strptime(issued_date_str, "%a %d %B, %Y at %H:%M")
    tz_vu = timezone(timedelta(hours=11))
    issued_at = issued_at.replace(tzinfo=tz_vu)
    return issued_at.astimezone(timezone.utc)


async def get_latest_page(
    db_session: AsyncSession,
    url: str | None,
) -> models.Page | None:
    query = select(models.Page).order_by(models.Page.fetched_at.desc())
    if url:
        query = query.where(models.Page.url == url)
    return (
        await db_session.execute(
            query.limit(1)
        )
    ).scalar()


def _save_html(html: str, fp: Path) -> Path:
    vmgd_directory = Path(config.ROOT_DIR) / "data" / "vmgd"
    if fp.is_absolute():
        if not fp.is_relative_to(vmgd_directory):
            raise Exception(f"Bad path for saving html {fp}")
    else:
        fp = vmgd_directory / fp
        if not fp.parent.exists():
            fp.parent.mkdir(parents=True)
    fp.write_text(html)
    return fp


async def handle_page_error(
    db_session: AsyncSession,
    url,
    description,
    html,
    raw_data,
    errors,
) -> models.PageError | None:
    """make page error or increment counter on existing error"""
    logger.warning(f"Page error {description} for {url}")
    html_hash = hashlib.md5(html.encode("utf-8")).hexdigest()
    result = await db_session.execute(
        select(models.PageError).where(
            models.PageError.url == url,
            models.PageError._description == description,
            models.PageError.html_hash == html_hash,
            models.PageError._raw_data == json.dumps(raw_data),
            models.PageError._errors == json.dumps(errors),
        )
        .limit(1)
    )
    existing = result.scalars().one_or_none()
    if existing:
        existing.count += 1
        existing.updated_at = now()
        db_session.add(existing)
        await db_session.commit()
    else:
        fp = models.PageError.get_html_directory() / html_hash
        _save_html(html, fp)
        page_error = models.PageError(
            url=url,
            description=description,
            html_hash=html_hash,
            raw_data=raw_data,
            errors=errors,
        )
        db_session.add(page_error)
        await db_session.commit()
