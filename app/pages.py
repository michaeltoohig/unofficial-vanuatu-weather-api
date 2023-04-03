"""Actions related to the VMGD pages."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import uuid
from sqlalchemy import select 
# from sqlalchemy.orm import joinedload

from app import config, models
from app.database import AsyncSession


def process_issued_at(text: str, delimiter_start: str, delimiter_end: str = "(utc time") -> datetime:
    """Given a text containing the `issued_at` value found between two delimiters extract the value and convert to a datetime.
    The general date format appears to be "%a %dXX %B, %Y at %H:%M" where `%dXX` is an ordinal number.
    Examples:
     - "Mon 27th March, 2023 at 15:02 (UTC Time:04:02)"
     - "Tue 28th March, 2023 at 16:05 (UTC Time:05:05)"
    
    So far I noticed the format of the date appears consistent across pages but the delimiter for the start of the date is inconsistent.
    """
    issued_date_str = text.lower().split(delimiter_start.lower(), 1)[1].split(delimiter_end.lower())[0].strip()
    issued_date_str = issued_date_str[:6] + issued_date_str[8:]  # remove 'st', 'nd', 'rd', 'th'
    issued_at = datetime.strptime(issued_date_str, "%a %d %B, %Y at %H:%M")
    tz_vu = timezone(timedelta(hours=11))
    issued_at = issued_at.replace(tzinfo=tz_vu)
    return issued_at.astimezone(timezone.utc)


async def get_latest_page(
    db_session: AsyncSession,
) -> models.Page | None:
    return (
        (
            await db_session.execute(
                select(models.Page)
                .order_by(models.Page.fetched_at.desc())
                .limit(1)
            )
        )
        .scalar()
    )


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
    html,
    raw_data,
    errors,
) -> models.PageError | None:
    # TODO should probably take the exc which contains the values we need
    """make error hash and return page error existing that matches"""
    existing = (
        await db_session.execute(
            select(models.PageError)
            .where(
                models.PageError._raw_data == json.dumps(raw_data),
                models.PageError.errors == json.dumps(errors),
            )
        )
    )
    if existing:
        pass  # TODO increment count on row
    else:
        pass  # save_html, hash html contents, save page error
    # filename = Path("errors") / str(uuid.uuid4())
    # filepath = _save_html(html, filename)