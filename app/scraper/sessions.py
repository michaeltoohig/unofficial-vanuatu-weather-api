

from dataclasses import dataclass
import enum

from app.scraper.pages import PageMapping
from app.scraper.scrapers import scrape_forecast, scrape_public_forecast_7_day
from app.scraper.aggregators import aggregate_forecast_week


@dataclass
class SessionMapping:
    name: str
    pages: list[PageMapping]
    process: callable  # processes results from PageMappings


class SessionName(enum.Enum):
    GENERAL_FORECAST = "forecast_general"


session_mappings = [
    SessionMapping(
        name=SessionName.GENERAL_FORECAST,
        pages=[
            PageMapping("/forecast-division", scrape_forecast),
            PageMapping(
                "/forecast-division/public-forecast/7-day", scrape_public_forecast_7_day
            ),
        ],
        process=aggregate_forecast_week,
    ),
]


# async def handle_session_error ???