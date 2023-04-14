


from dataclasses import dataclass
from typing import List


@dataclass
class ForecastEntity:
    page_mappings: List[PageMapping]

    def build_forecast(self):
        forecast_data = {}
        for mapping in self.page_mappings:
            scraper = mapping.scraper
            page_data = scraper(mapping.url)
            forecast_data.update(page_data)

        forecast = ForecastModel(**forecast_data)
        return forecast

# TODO more entities