"""Functions that handle the messy work of aggregating and cleaning the results of scrapers."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from cerberus_list_schema import Validator as ListValidator
from cerberus import Validator, SchemaError
from loguru import logger

from app.database import AsyncSession, async_session
from app.locations import get_location_by_name, save_forecast_location
from app.models import Location
from app.vmgd.schemas import (
    process_forecast_schema,
    process_public_forecast_7_day_schema,
)


@dataclass
class ForecastDailyIn(frozen=True, kw_only=True):
    location: Location
    date: datetime
    summary: str
    minX: int
    maxX: int
    minY: int
    maxY: int


@dataclass
class WeatherData:
    location: str
    latitude: float
    longitude: float
    dates: List[str]
    minX: List[int]
    maxX: List[int]
    minY: List[int]
    maxY: List[int]
    conds: List[int]
    wd: List[float]
    ws: List[int]
    dtFlag: int
    currentDate: str
    dateHour: List[str]


async def handle_location(l, d1, d2):
    dlist = []
    for date, minX, maxX, minY, minY, maxY, x in zip(d1.dates, d1.minX, d1.maxX, d1.minY, d1.maxY, d2):
        assert x["date"] == date, "d mismatch"
        d = ForecastDailyIn(location=l, date=date, minX=minX, maxX=maxX, minY=minY, maxY=maxY)



async def aggregate_forecast_week(data):
    """Handles forecast forecast data which currently comprises of 7-day forecast and 3 day forecast.
    Together the two pages can form a coherent weekly forecast."""

    issued_at_1, data_1 = data[0]
    issued_at_2, data_2 = data[1]
    # confirm both data sets have all locations
    assert set(map(lambda d: d[0], data_1)) == set(map(lambda d: d["location"], data_2))

    for data in data_1:
        # v = ListValidator(process_forecast_schema)
        # data = v.normalized_as_dict(data)
        data = WeatherData(*data)
        async with async_session() as db_session:
            location = await save_forecast_location(
                db_session, data.location, data.latitude, data.longitude,
            )
            ldata1 = data
            ldata2 = list(filter(lambda x: x["location"].lower() == location.name.lower(), data_2))
            await handle_location(location, ldata1, ldata2)


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
