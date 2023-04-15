

from dataclasses import dataclass
from typing import List

from app.scraper.mappings import PageMapping


@dataclass
class ForecastEntity:
    page_mappings: List[PageMapping]
    # aggregator: callable | None = None  <-- example to replace self.scrape

    # this is probably unnecessary... most pages are scraped just the same as far as I can see.
    # maybe set an aggregate function callable then if needed replace it per entity
    def scrape(self):
        page_data = {}
        for mapping in self.page_mappings:
            """
            data = process_page(mapping.url)  # rename to scrape_page have another form of the same function for process_page_image, etc to handle pages with image data, etc.
            page_data.update(data)
            """

    def process(self, data_1, data_2):
        pass
        # process extensive work but then save to database like our current aggregate_forecast_data function


@dataclass
class ForecastMedia:
    page: PageMapping

    def scrape(self):
        pass

    def process(self):
        pass
