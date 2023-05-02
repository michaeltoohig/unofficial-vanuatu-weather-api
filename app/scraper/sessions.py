

from dataclasses import dataclass
import enum

from app.scraper.pages import PageMapping, PagePath
from app.scraper.scrapers import scrape_current_bulletin, scrape_forecast, scrape_public_forecast_7_day, scrape_public_forecast_media, scrape_severe_weather_outlook, scrape_severe_weather_warning
from app.scraper.aggregators import aggregate_forecast_week, aggregate_severe_weather_warning


@dataclass
class SessionMapping:
    name: str
    pages: list[PageMapping]
    process: callable  # processes results from PageMappings


class SessionName(enum.Enum):
    FORECAST_GENERAL = "forecast_general"
    FORECAST_MEDIA = "forecast_media"
    WARNING_BULLETIN = "warning_bulletin"
    WARNING_SEVERE_WEATHER = "warning_severe_weather"


session_mappings = [
    # SessionMapping(
    #     name=SessionName.FORECAST_GENERAL,
    #     pages=[
    #         PageMapping(PagePath.FORECAST_MAP, scrape_forecast),
    #         PageMapping(PagePath.FORECAST_WEEK, scrape_public_forecast_7_day),
    #     ],
    #     process=aggregate_forecast_week,
    # ),
    # SessionMapping(
    #     name=SessionName.FORECAST_MEDIA,
    #     pages=[PageMapping(PagePath.FORECAST_MEDIA, scrape_public_forecast_media)],
    #     process=None,
    # ),
    # SessionMapping(
    #     name=SessionName.WARNING_BULLETIN,
    #     pages=[PageMapping(PagePath.WARNING_BULLETIN, scrape_current_bulletin)],
    #     process=None,
    # ),
    SessionMapping(
        name=SessionName.WARNING_SEVERE_WEATHER,
        pages=[PageMapping(PagePath.WARNING_SEVERE_WEATHER, scrape_severe_weather_warning)],
        process=aggregate_severe_weather_warning,
    ),
]


# async def handle_session_error ???