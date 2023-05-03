from dataclasses import field, dataclass
from datetime import datetime
from typing import Any


@dataclass
class LocationResponse:
    id: int
    name: str
    latitude: float
    longitude: float


@dataclass
class RawPageResponse:
    url: str
    data: Any


@dataclass
class ForecastResponse:
    location: int
    date: datetime
    summary: str
    minTemp: int
    maxTemp: int
    minHumi: int
    maxHumi: int


@dataclass
class WarningResponse:
    date: datetime
    body: str