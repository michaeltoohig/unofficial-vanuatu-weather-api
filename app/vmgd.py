import httpx

from app import config
from app.utils.datetime import now


class VMGDWebPage:
    def __init__(self, url) -> None:
        self.url = url
        self.html = None
        self.fetched_at = None

    async def fetch(self):
        """Fetch the HTML of the given URL."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.url,
                headers={
                    "User-Agent": config.USER_AGENT,
                },
                follow_redirects=True,
            )
            self.html = resp
            # TODO save html locally for review or debug when issues occur
            self.fetched_at = now()
            
    def extract(self):
        """Handle the particulars of extracting cleaned data from the fetched HTML."""
        raise NotImplementedError

    def save(self):
        """Save the extracted data to persistent storage."""
        raise NotImplementedError    


page_severe_weather = VMGDWebPage("https://www.vmgd.gov.vu/vmgd/index.php/forecast-division/warnings/severe-weather-warning")
page_severe_marine = VMGDWebPage("https://www.vmgd.gov.vu/vmgd/index.php/forecast-division/warnings/marine-warning")