from datetime import date, datetime, timedelta, timezone, time
from typing import Annotated

from fastapi import Depends, Query


def now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc)


def as_vu_to_utc(dt: datetime) -> datetime:
    tz_vu = timezone(timedelta(hours=11))  # hardcoded value for our target data source
    dt = dt.replace(tzinfo=tz_vu)
    return dt.astimezone(timezone.utc)


def get_datetime_dependency(d: date = Query(None, alias="date")):
    if d is None:
        return None
    return as_utc(datetime.combine(d, time(0, 0)))


DateDep = Annotated[datetime, Depends(get_datetime_dependency)]