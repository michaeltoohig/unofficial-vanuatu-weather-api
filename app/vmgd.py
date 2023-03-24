from pathlib import Path

import anyio
import httpx
from loguru import logger

from app.config import ROOT_DIR, USER_AGENT
from app.utils.datetime import now


BASE_URL = "https://www.vmgd.gov.vu/vmgd/index.php"


async def fetch_all_pages(db_session) -> None:
    pass


async def run_fetch_all_pages() -> None:
    """CLI entrypoint."""
    headers = {
        "User-Agent": USER_AGENT,
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        async with anyio.create_task_group() as tg:
            tg.start_soon(_fetch_forecast, client)
            tg.start_soon(_fetch_public_forecast, client)
            tg.start_soon(_fetch_public_forecast_policy, client)
            tg.start_soon(_fetch_severe_weather_outlook, client)
            tg.start_soon(_fetch_public_forecast_tc_outlook, client)
            tg.start_soon(_fetch_public_forecast_7_day, client)
            tg.start_soon(_fetch_public_forecast_media, client)
            tg.start_soon(_fetch_current_bulletin, client)
            tg.start_soon(_fetch_severe_weather_warning, client)
            tg.start_soon(_fetch_marine_waring, client)
            tg.start_soon(_fetch_hight_seas_warning, client)


async def _fetch(client: httpx.AsyncClient, url) -> httpx.Response:
    """Fetch the web page.
    Currently we store a cached copy for development purposes but in the future I will
    keep the `/data/vmgd` directory to store pages that fail scraping for debugging.
    """
    slug = url.rsplit("/", 1)[1]
    url = BASE_URL + url
    cached_page = Path(ROOT_DIR / "data" / "vmgd" / slug)
    if not cached_page.exists():
        logger.info(f"Fetching {url=}")
        # TODO retry httpx.ConnectError
        resp = await client.get(url)
        if resp.status_code == httpx.codes.OK:
            cached_page.write_text(resp.text)
        else:
            # TODO handle 404 or 500 or if we become blocked or something
            resp.raise_for_status()
    else:
        logger.info(f"Fetching page from cache {slug=}")
        resp = cached_page.read_text()
    return resp


async def _fetch_forecast(client: httpx.AsyncClient) -> None:
    """The main forecast page with daily temperature and humidity information and 6 hour
    interval resolution for weather condition, wind speed/direction.
    """
    url = "/forecast-division"
    resp = await _fetch(client, url)


# Public Forecast
#################


async def _fetch_public_forecast(client: httpx.AsyncClient) -> None:
    """The about page of the weather forecast section.

    TODO collect the main about text and hash it; store the hash and date collected in a
    directory so that only when the hash changes do we save a new page. This can also
    alert us to changes in the about page which may signal other important changes to
    how data is collected and reported in other forecast pages.
    """
    url = "/forecast-division/public-forecast"
    resp = await _fetch(client, url)


async def _fetch_public_forecast_policy(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/public-forecast/forecast-policy"
    resp = await _fetch(client, url)


async def _fetch_severe_weather_outlook(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/public-forecast/severe-weather-outlook"
    resp = await _fetch(client, url)


async def _fetch_public_forecast_tc_outlook(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/public-forecast/tc-outlook"
    resp = await _fetch(client, url)


async def _fetch_public_forecast_7_day(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/public-forecast/7-day"
    resp = await _fetch(client, url)


async def _fetch_public_forecast_media(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/public-forecast/media"
    resp = await _fetch(client, url)


# Warnings
##########


async def _fetch_current_bulletin(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/warnings/current-bulletin"
    resp = await _fetch(client, url)


async def _fetch_severe_weather_warning(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/warnings/severe-weather-warning"
    resp = await _fetch(client, url)


async def _fetch_marine_waring(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/warnings/marine-warning"
    resp = await _fetch(client, url)


async def _fetch_hight_seas_warning(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/warnings/hight-seas-warning"
    resp = await _fetch(client, url)
