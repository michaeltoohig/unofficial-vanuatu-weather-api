from dataclasses import dataclass
from datetime import datetime


@dataclass
class WeatherObject:
    location: str
    latitude: float
    longitude: float
    dates: list[str]
    minTemp: list[int]
    maxTemp: list[int]
    minHumi: list[int]
    maxHumi: list[int]
    conds: list[int]
    wd: list[float]
    ws: list[int]
    dtFlag: int
    currentDate: str
    dateHour: list[str]


process_forecast_schema = {
    "type": "list",
    "items": [
        {
            "type": "string",
            "name": "location",
        },
        {
            "type": "float",
            "name": "latitude",
        },
        {
            "type": "float",
            "name": "longitude",
        },
        {
            "type": "list",
            "name": "date",
            "items": [{"type": "string"} for _ in range(8)],
        },
        {
            "type": "list",
            "name": "minTemp",
            "items": [{"type": "integer"} for _ in range(7)],
        },
        {
            "type": "list",
            "name": "maxTemp",
            "items": [{"type": "integer"} for _ in range(7)],
        },
        {
            "type": "list",
            "name": "minHumi",
            "items": [{"type": "integer"} for _ in range(7)],
        },
        {
            "type": "list",
            "name": "maxHumi",
            "items": [{"type": "integer"} for _ in range(7)],
        },
        {
            "type": "list",
            "name": "weatherCondition",
            "items": [{"type": "integer"} for _ in range(16)],
        },
        {
            "type": "list",
            "name": "windDirection",
            "items": [{"type": "float"} for _ in range(16)],
        },
        {
            "type": "list",
            "name": "windSpees",
            "items": [{"type": "integer"} for _ in range(16)],
        },
        {
            "type": "integer",
            "name": "dtFlag",
        },
        {
            "type": "string",
            "name": "currentDate",
        },
        {
            "type": "list",
            "name": "dateHour",
            "items": [{"type": "string"} for _ in range(16)],
        },
    ],
}


process_public_forecast_7_day_schema = {
    "location": {"type": "string", "empty": False},
    "date": {"type": "string", "empty": False},
    "summary": {"type": "string"},
    "minTemp": {"type": "integer", "coerce": int},
    "maxTemp": {"type": "integer", "coerce": int},
}
