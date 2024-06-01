from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.scraper.scrapers import NO_CURRENT_WARNING


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
class RawSessionResponse:
    name: str
    success: bool
    started_at: datetime | None = None  # XXX maybe remove this optional


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
class ForecastMediaResponse:
    summary: str
    images: list[str] | None = None


@dataclass
class WeatherWarningResponse:
    date: datetime
    name: str
    body: str | None

    def __post_init__(self):
        if self.body is None:
            self.body = NO_CURRENT_WARNING