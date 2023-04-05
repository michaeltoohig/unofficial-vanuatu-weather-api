from datetime import datetime, timedelta, timezone


def now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc)


def as_vu_to_utc(dt: datetime) -> datetime:
    tz_vu = timezone(timedelta(hours=11))  # hardcoded value for our target data source
    dt = dt.replace(tzinfo=tz_vu)
    return dt.astimezone(timezone.utc)