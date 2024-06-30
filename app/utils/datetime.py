from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, Query
from pydantic import BaseModel, validator, ValidationError
import sqlalchemy as sa

TZ_VU = timezone(timedelta(hours=11))  # hardcoded value for our target data source


def now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc)


def as_vu_to_utc(dt: datetime) -> datetime:
    dt = dt.replace(tzinfo=TZ_VU)
    return dt.astimezone(timezone.utc)


def as_vu(dt: datetime) -> datetime:
    return dt.astimezone(TZ_VU)


class UTCDateTime(sa.types.TypeDecorator):

    impl = sa.types.DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, engine):
        if value is not None:
            return value.astimezone(timezone.utc)

    def process_result_value(self, value, engine):
        if value is not None:
            return value.replace(tzinfo=timezone.utc)


class DateTimeQuery(BaseModel):
    date: Optional[str] = None

    @validator("date")
    def validate_date(cls, value):
        if value is None:
            return value

        try:
            # Try to parse as ISO date
            parsed_date = datetime.fromisoformat(value)
        except ValueError:
            try:
                # Try to parse as ISO datetime without timezone
                parsed_date = datetime.fromisoformat(value + "Z")
            except ValueError:
                try:
                    # Parse as ISO datetime with timezone
                    parsed_date = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
                except ValueError:
                    raise ValueError("Invalid date format")

        # Convert to UTC datetime
        return parsed_date.astimezone(timezone.utc)


def get_datetime_dependency(date: str = Query(None)):
    """
    Returns UTC datetime from ISO formatted datetime string in query.
    """
    if date is None:
        return None

    try:
        query = DateTimeQuery(date=date)
        return query.date
    except ValidationError as e:
        raise ValueError(f"Invalid date format: {e}")


DateDep = Annotated[datetime, Depends(get_datetime_dependency)]
