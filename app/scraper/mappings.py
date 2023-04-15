
from dataclasses import dataclass
from app.config import BASE_URL
from app.scraper.entities import ForecastEntity, ForecastMedia

from app.scraper.scrapers import scrape_forecast, scrape_public_forecast_7_day, scrape_public_forecast_media

# TODO this whole file is unnecessary if I define a PageMapping inline with its entity class
# TODO rename process to scrape
# - remove large 


@dataclass
class PageMapping:
    relative_url: str
    process: callable
    # process_images: callable | None  # TODO decide how to handle pages that have images.
    # either a new process step to define for each page
    # or better yet return an 'images' key with the process results and treat that key special in the `process_page` function
    # the next level would be to save `PageImage` models as children of the Page model to keep them sorted and to prevent saving duplicate images store image hashes there, etc.
    # TODO figure it out next time to continue here

    @property
    def url(self):
        return BASE_URL + self.relative_url

    @property
    def slug(self):
        return self.relative_url.rsplit("/", 1)[1]


entities = [
    ForecastEntity([
        PageMapping("/forecast-division", scrape_forecast),
        PageMapping(
            "/forecast-division/public-forecast/7-day", scrape_public_forecast_7_day
        ),
    ]),
    ForecastMedia(PageMapping(
        "/forecast-division/public-forecast/media", scrape_public_forecast_media
    ))
]


async def run_process_all_entities() -> None:
    # TODO 
    pass


async def run_process_all_pages() -> None:
    """CLI entrypoint."""
    # TODO
    for entity in entities:
        entity.scrape()
        entity.process()
        # etc... WIP


# pages_to_fetch = [
#     PageMapping("/forecast-division", process_forecast),
#     # PageMapping("/forecast-division/public-forecast", process_public_forecast),
#     # PageMapping(
#     #     "/forecast-division/public-forecast/forecast-policy",
#     #     process_public_forecast_policy,
#     # ),
#     # PageMapping(
#     #     "/forecast-division/public-forecast/severe-weather-outlook",
#     #     process_severe_weather_outlook,
#     # ),
#     # PageMapping(
#     #     "/forecast-division/public-forecast/tc-outlook",
#     #     process_public_forecast_tc_outlook,
#     # ),
#     PageMapping(
#         "/forecast-division/public-forecast/7-day", process_public_forecast_7_day
#     ),
#     PageMapping(
#         "/forecast-division/public-forecast/media", process_public_forecast_media
#     ),
#     # PageMapping(
#     #     "/forecast-division/warnings/current-bulletin", process_current_bulletin
#     # ),
#     # PageMapping(
#     #     "/forecast-division/warnings/severe-weather-warning",
#     #     process_severe_weather_warning,
#     # ),
#     # PageMapping("/forecast-division/warnings/marine-warning", process_marine_waring),
#     # PageMapping(
#     #     "/forecast-division/warnings/hight-seas-warning", process_hight_seas_warning
#     # ),
# ]


# # TODO remove - use entities instead
# page_sets = [
#     PageSet(
#         pages = [
#             PageMapping("/forecast-division", process_forecast),
#             PageMapping(
#                 "/forecast-division/public-forecast/7-day", process_public_forecast_7_day
#             ),
#         ],
#         process = aggregate_forecast_data, 
#     ),
# ]