"""Actions related to the VMGD pages."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select 
# from sqlalchemy.orm import joinedload

from app import models
from app.database import AsyncSession


def extract_issued_at_datetime(text: str, delimiter_start: str, delimiter_end: str = "(utc time") -> datetime:
    """Given a text containing the `issued_at` value extract the value found between the two delimiters.
    The general date format appears to be "%a %dXX %B, %Y at %H:%M" where `%dXX` is an ordinal number.
    Examples:
     - "Mon 27th March, 2023 at 15:02 (UTC Time:04:02)"
     - "Tue 28th March, 2023 at 16:05 (UTC Time:05:05)"
    
    So far I noticed the format of the date appears consistent but the delimiter for the start of the date is inconsistent.
    """
    issued_date_str, issued_time_str = text.split(delimiter_start.lower(), 1)[1].split(delimiter_end.lower())[0].strip()
    issued_date_str = issued_date_str[:6] + issued_date_str[8:]  # remove 'st', 'nd', 'rd', 'th'
    issued_at = datetime.strptime(issued_date_str, "%a %d %B, %Y at %H:%M")
    # issued_at = datetime.combine(date=issued_at.date(), time=datetime.strptime(issued_time_str, "%H:%M").time())
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