import httpx

from app.database import AsyncSession, async_session
from app.scraper.entities import ForecastEntity, ForecastMedia
from app.scraper.pages import PageMapping
from app.scraper.scrapers import (
    default_scrape_wrapper,
    scrape_forecast,
    scrape_public_forecast_7_day,
    scrape_public_forecast_media,
)


entities = [
    ForecastEntity(
        [
            PageMapping(
                "/forecast-division",
                process=scrape_forecast,
                scraper=default_scrape_wrapper,
            ),
            PageMapping(
                "/forecast-division/public-forecast/7-day",
                process=scrape_public_forecast_7_day,
                scraper=default_scrape_wrapper,
            ),
        ]
    ),
    # ForecastMedia(PageMapping(
    #     "/forecast-division/public-forecast/media", scrape_public_forecast_media, scrape_page_with_image,
    # ))
]


async def run_process_all_entities() -> None:
    # TODO
    pass


async def run_process_all_entities() -> None:
    """CLI entrypoint."""
    async with httpx.AsyncClient() as client:
        for entity in entities:
            entity_data = {}
            async with async_session() as db_session:
                for mapping in entity.page_mappings:
                    page_data = await mapping.scraper(db_session, mapping)
                    entity_data.append(page_data)
                await entity.process(entity_data)
        # etc... WIP


# NOTE alternative approach that doesn't require Entity classes but just a file containing aggregation functions
# page_sets = [
#     Entity(
#         pages = [
#             PageMapping("/forecast-division", process_forecast),
#             PageMapping(
#                 "/forecast-division/public-forecast/7-day", process_public_forecast_7_day
#             ),
#         ],
#         appgregate = aggregate_forecast_data,
#     ),
# ]
