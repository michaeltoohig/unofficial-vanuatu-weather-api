from datetime import date, datetime, timedelta, timezone, time
from typing import Annotated

from fastapi import Depends, Query
import sqlalchemy as sa


def now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc)


def as_vu_to_utc(dt: datetime) -> datetime:
    tz_vu = timezone(timedelta(hours=11))  # hardcoded value for our target data source
    dt = dt.replace(tzinfo=tz_vu)
    return dt.astimezone(timezone.utc)


class UTCDateTime(sa.types.TypeDecorator):

    impl = sa.types.DateTime(timezone=True)
    cache_ok = True
    def process_bind_param(self, value, engine):
        if value is not None:
            return value.astimezone(timezone.utc)
    def process_result_value(self, value, engine):
        if value is not None:
            return value.replace(tzinfo=timezone.utc)


def get_datetime_dependency(date: str = Query(None, regex="^(\d{4}-\d{2}-\d{2})|(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{6})|(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{6}Z)|([+-]\\d{2}:\\d{2})$")):
    """
    Returns UTC datetime from ISO formatted datetime string in query.
    """
    if date is None:
        return None

    try:
        # Try to parse as ISO date
        parsed_date = datetime.fromisoformat(date)
    except ValueError:
        try:
            # Try to parse as ISO datetime without timezone
            parsed_date = datetime.fromisoformat(date + "Z")
        except ValueError:
            # Parse as ISO datetime with timezone
            parsed_date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%f%z")
    
    # Convert to UTC datetime
    d = parsed_date.astimezone(timezone.utc)
    print(d)
    return d


DateDep = Annotated[datetime, Depends(get_datetime_dependency)]
