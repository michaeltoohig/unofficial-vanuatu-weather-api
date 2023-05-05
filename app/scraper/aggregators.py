"""Functions that handle the messy work of aggregating and cleaning the results of scrapers."""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from loguru import logger

from app.database import AsyncSession
from app.locations import save_forecast_location
from app.models import ForecastDaily, Location, Page, Session, WeatherWarning
from app.scraper.schemas import WeatherObject
from app.scraper.scrapers import NO_CURRENT_WARNING
from app.utils.datetime import as_utc, as_vu_to_utc, now


@dataclass(frozen=True, kw_only=True)
class ForecastDailyCreate:
    location_id: int
    date: datetime
    summary: str
    minTemp: int
    maxTemp: int
    minHumi: int
    maxHumi: int


async def handle_location(l: Location, wo: WeatherObject, d2):
    forecasts = []
    for date, minTemp, maxTemp, minHumi, maxHumi, x in zip(
        wo.dates,
        wo.minTemp,
        wo.maxTemp,
        wo.minHumi,
        wo.maxHumi,
        d2,
    ):
        assert x["date"] == date, "d mismatch"
        forecast = ForecastDailyCreate(
            location_id=l.id,
            date=date,
            summary=x["summary"],
            minTemp=min(x["minTemp"], minTemp),
            maxTemp=max(x["maxTemp"], maxTemp),
            minHumi=minHumi,
            maxHumi=maxHumi,
        )
        forecasts.append(forecast)
    return forecasts


def convert_to_datetime(date_string: str, issued_at: datetime) -> datetime:
    """Convert human readable date string such as `Friday 24` or `Fri 24` to datetime.
    We can do this assuming the following:
     - the `issued_at` value is never before the `date_string`
     - the `date_string` is never representing a value greater than 1 month after the `issued_at` date
    # TODO it is possible to find issued_at greater than date_string by a day or two - NOT HANDLED
    """
    day = int(date_string.split()[1])
    if day < issued_at.day:
        # we have wrapped around to a new month/year
        next_month = issued_at + relativedelta(months=1)
        dt = datetime(next_month.year, next_month.month, day)
    else:
        dt = datetime(issued_at.year, issued_at.month, day)
    return as_utc(dt)


def is_date_series_sequential(dates_list: list[datetime]):
    """Checks dates are sequentially ordered."""
    prev_date = dates_list[0]
    for i in range(1, len(dates_list)):
        curr_date = dates_list[i]
        if prev_date + timedelta(days=1) != curr_date:
            return False
        prev_date = curr_date
    return True


def verify_date_series(dates_list: list[datetime]) -> int:
    """Checks dates are sequentially ordered ."""
    logger.info(dates_list)
    if is_date_series_sequential(dates_list):
        return dates_list
    logger.debug("Dates are not sequential - attempting to fix common ambiguity issue")
    dl = list(dates_list)
    for i in range(len(dates_list) - 1):
        dl[i] = dl[i] - relativedelta(months=1)
        if is_date_series_sequential(dl):
            return dl
    else:
        raise RuntimeError("Can not fix non-sequential dates")


async def aggregate_forecast_week(
    db_session: AsyncSession, session: Session, pages: list[Page]
):
    """Handles data which currently comprises of 7-day forecast and 3 day forecast.
    Together the two pages can form a coherent weekly forecast."""
    location_cache = {}

    weather_objects = list(map(lambda obj: WeatherObject(*obj), pages[0].raw_data))
    data_2 = pages[1].raw_data

    # confirm both issued_at are the same date
    assert pages[0].issued_at.date() == pages[1].issued_at.date()
    issued_at = pages[0].issued_at

    # confirm both data sets have all locations
    assert set(map(lambda wo: wo.location, weather_objects)) == set(
        map(lambda d: d["location"], data_2)
    )

    # convert string dates to datetimes
    for wo in weather_objects:
        datetimes = list(map(lambda d: convert_to_datetime(d, issued_at), wo.dates))
        datetimes = verify_date_series(datetimes)
        wo.dates = datetimes
    for d in data_2:
        datetimes = convert_to_datetime(d["date"], issued_at)
        datetimes = verify_date_series(datetimes)
        d["date"] = datetimes

    for wo in weather_objects:
        if wo.location in location_cache:
            location = location_cache[wo.location]
        else:
            location = await save_forecast_location(
                db_session,
                wo.location,
                wo.latitude,
                wo.longitude,
            )
            location_cache[wo.location] = location
        ldata2 = list(
            filter(lambda x: x["location"].lower() == location.name.lower(), data_2)
        )
        forecasts = await handle_location(location, wo, ldata2)
        for forecast_create in forecasts:
            forecast = ForecastDaily(**asdict(forecast_create))
            forecast.issued_at = issued_at
            forecast.session_id = session.id
            db_session.add(forecast)


def convert_warning_at_to_datetime(text: str, delimiter_start: str = ": ") -> datetime:
    """Convert warning date string to datetime.
    Examples:
     - "Friday 24th March, 2023"
     - "Tuesday 2nd May, 2023"
    """
    # Prep the string
    issued_date_str = text.lower().split(delimiter_start.lower(), 1)[1].strip()
    issued_date_parts = issued_date_str.split()
    issued_day = issued_date_parts[1][:-2]  # remove 'st', 'nd', 'rd', 'th'
    issued_date_parts[1] = issued_day
    issued_date_str = " ".join(issued_date_parts)
    # Parse the string
    issued_at = datetime.strptime(issued_date_str, f"%A %d %B, %Y")
    return as_vu_to_utc(issued_at)


# async def aggregate_severe_weather_warning(
async def aggregate_weather_warnings(
    db_session: AsyncSession, session: Session, pages: list[Page]
):
    """Handles data from the severe weather warnings."""
    # TODO convert warning_ojects to a proper object like a dataclass before it arrives here?
    issued_at = pages[0].issued_at
    raw_data = pages[0].raw_data
    if raw_data == NO_CURRENT_WARNING:
        new_warning = WeatherWarning(
            session_id=session.id,
            issued_at=issued_at,
            date=now(),
        )
        db_session.add(new_warning)
    else:
        for warning_object in raw_data:
            date = convert_warning_at_to_datetime(warning_object["date"])
            new_warning = WeatherWarning(
                session_id=session.id,
                issued_at=issued_at,
                date=date,
                body=warning_object["body"],
            )
            db_session.add(new_warning)
