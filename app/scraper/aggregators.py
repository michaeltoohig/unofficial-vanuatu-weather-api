"""Functions that handle the messy work of aggregating and cleaning the results of scrapers."""

from dataclasses import asdict, dataclass
from datetime import datetime
from dateutil.relativedelta import relativedelta

from loguru import logger

from app.database import AsyncSession
from app.locations import save_forecast_location
from app.models import ForecastDaily, Location, Page, Session
from app.scraper.schemas import WeatherObject


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
    """
    day = int(date_string.split()[1])
    if day < issued_at.day:
        # we have wrapped around to a new month/year
        next_month = issued_at + relativedelta(months=1)
        dt = datetime(next_month.year, next_month.month, day)
    else:
        dt = datetime(issued_at.year, issued_at.month, day)
    return dt


async def aggregate_forecast_week(
    db_session: AsyncSession, session: Session, pages: list[Page]
):
    """Handles forecast forecast data which currently comprises of 7-day forecast and 3 day forecast.
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
        wo.dates = datetimes
    for d in data_2:
        d["date"] = convert_to_datetime(d["date"], issued_at)

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
