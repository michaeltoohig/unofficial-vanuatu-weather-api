"""Functions that handle the messy work of aggregating and cleaning the results of scrapers."""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List

from cerberus_list_schema import Validator as ListValidator
from cerberus import Validator, SchemaError
from loguru import logger

from app.database import AsyncSession, async_session
from app.locations import get_location_by_name, save_forecast_location
from app.models import ForecastDaily, Location
from app.vmgd.schemas import (
    WeatherObject,
    process_forecast_schema,
    process_public_forecast_7_day_schema,
)


@dataclass(frozen=True, kw_only=True)
class ForecastDailyCreate:
    location: Location
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
            location=l,
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
    if day <= issued_at.day:
        # we have wrapped around to a new month/year
        next_month = issued_at + relativedelta(months=1)
        dt = datetime(next_month.year, next_month.month, day)
    else:
        dt = datetime(issued_at.year, issued_at.month, day)
    return dt


async def aggregate_forecast_week(fetched_at: datetime, data):
    """Handles forecast forecast data which currently comprises of 7-day forecast and 3 day forecast.
    Together the two pages can form a coherent weekly forecast."""

    issued_at_1, weather_objects = data[0]
    issued_at_2, data_2 = data[1]

    # confirm both issued_at are the same date
    assert issued_at_1.date() == issued_at_2.date()

    # confirm both data sets have all locations
    assert set(map(lambda wo: wo.location, weather_objects)) == set(
        map(lambda d: d["location"], data_2)
    )
    
    # convert string dates to datetimes
    for wo in weather_objects:
        datetimes = list(map(lambda d: convert_to_datetime(d, issued_at_1), wo.dates))
        wo.dates = datetimes
    for d in data_2:
        d["date"] = convert_to_datetime(d["date"], issued_at_1)

    for wo in weather_objects:
        async with AsyncSession() as db_session:
            location = await save_forecast_location(
                db_session,
                wo.location,
                wo.latitude,
                wo.longitude,
            )
        ldata2 = list(
            filter(lambda x: x["location"].lower() == location.name.lower(), data_2)
        )
        forecasts = await handle_location(location, wo, ldata2)
        for forecast_create in forecasts:
            forecast = ForecastDaily(**asdict(forecast_create))
            forecast.issued_at = issued_at_1
            forecast.fetched_at = fetched_at
            db_session.add(forecast)
        db_session.commit()

    return
    # --- below is just ... embarrassing
    issued_at_1, forecast_1 = data[0]
    issued_at_2, forecast_2 = data[1]

    locations_1 = set(map(lambda f: f[0], forecast_1))
    locations_2 = set(map(lambda f: f["location"], forecast_2))
    assert locations_1 == locations_2, "Forecast locations differ"

    # Organize data by location
    forecasts = {}
    for name in locations_1:
        forecast = {}
        data = next(filter(lambda x: x[0].lower() == name.lower(), forecast_1))
        v = ListValidator(
            process_forecast_schema
        )  # TODO add schema to PageMapping - Add result data to PageMapping so we fetch it from there instead of a param on the method
        normalized_data = v.normalized_as_dict(data)
        starting_dt = datetime.strptime(normalized_data["date"][0], "%a %d").replace(
            year=issued_at_1.year, month=issued_at_1.month
        )
        dates = {0: starting_dt}
        for i in range(1, len(normalized_data["date"].keys())):
            try:
                dates[i] = dates[i - 1] + timedelta(days=1)
                assert normalized_data["date"][i] == dates[i].strftime("%a %d")
            except:
                import pdb

                pdb.set_trace()
                pass
        normalized_data["date"] = dates
        forecast["data_1"] = normalized_data
        data = list(filter(lambda x: x["location"].lower() == name.lower(), forecast_2))
        starting_dt = datetime.strptime(data[0]["date"], "%A %d").replace(
            year=issued_at_2.year, month=issued_at_2.month
        )
        for i in data:
            assert True
        forecast["data_2"] = data

        # Save location with forecast
        async with async_session() as db_session:
            latitude = forecast["data_1"]["latitude"]
            longitude = forecast["data_1"]["longitude"]
            location = await save_forecast_location(
                db_session, name, latitude, longitude
            )
            forecast["location"] = location

        # TODO orgainize data for each location into forecast objects

        # assert issued_at_1.strftime("%a %d") == forecast["data_1"]["date"][0]

        # Create daily forecast objects
        fo = forecast["data_1"]
        wanted_keys = ["date", "minTemp", "maxTemp", "minHumi", "maxHumi"]
        results = []
        for i in range(6):  # 7 days
            newDict = {}
            for key, value in fo.items():
                if key in wanted_keys:
                    newDict[key] = value[i]
            # assert forecast["data_2"][i]["date"] == newDict["date"]
            newDict.update({"summary": forecast["data_2"][0]["summary"]})
            newDict.update({"location": forecast["location"]})
            results.append(newDict)

        # data = [{key: value[i] for key, value in data.items()} for i in range(len(next(iter(data.values()))))]
        data = []
        for i in range(len(forecast["data_1"]["date"]) - 1):
            fo = forecast["data_1"]
            try:
                da = dict(
                    date=fo["date"][i],
                    minTemp=fo["minTemp"][i],
                    maxTemp=fo["maxTemp"][i],
                    minHumi=fo["minHumi"][i],
                    maxHumi=fo["maxHumi"][i],
                    summary=None,
                )
                data.append(da)
            except KeyError:
                logger.debug(f"{name} has run short at index={i}")
        forecast["daily"] = data

        # Create quarterly forecast objects
        import pdb

        pdb.set_trace()

        data = []
        for i in range(len(forecast["data_2"])):
            pass

        # index 6/7 is daily humi values
    for location in forecast.keys():
        pass
