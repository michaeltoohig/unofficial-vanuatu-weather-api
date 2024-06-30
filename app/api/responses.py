from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Generic, TypeVar, List, Optional
import pytz

from app import config
from app.scraper.scrapers import NO_CURRENT_WARNING


class LocationResponseData(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float


class RawPageResponseData(BaseModel):
    url: str
    data: Any


class RawSessionResponseData(BaseModel):
    name: str
    success: bool
    started_at: datetime


class ForecastResponseData(BaseModel):
    location: int
    date: datetime
    summary: str
    minTemp: int
    maxTemp: int
    minHumi: int
    maxHumi: int

    def __init__(self, **data):
        super().__init__(**data)
        vu_tz = pytz.timezone("Pacific/Efate")
        self.date = self.date.astimezone(vu_tz)


class ForecastMediaResponseData(BaseModel):
    summary: str
    images: Optional[List[str]] = None


class WeatherWarningResponseData(BaseModel):
    date: datetime
    name: str
    body: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.body is None:
            self.body = NO_CURRENT_WARNING
        vu_tz = pytz.timezone("Pacific/Efate")
        self.date = self.date.astimezone(vu_tz)


class VmgdApiResponseMeta(BaseModel):
    issued: datetime
    fetched: datetime
    attribution: str = Field(default=config.VMGD_ATTRIBUTION)


class VmgdApiResponse(BaseModel):
    meta: VmgdApiResponseMeta


class VmgdApiForecastResponse(VmgdApiResponse):
    data: list[ForecastResponseData]


class VmgdApiForecastMediaResponse(VmgdApiResponse):
    data: ForecastMediaResponseData


class VmgdApiWeatherWarningResponse(VmgdApiResponse):
    data: WeatherWarningResponseData


class VmgdApiWeatherWarningsResponse(VmgdApiResponse):
    data: list[WeatherWarningResponseData]
