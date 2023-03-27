import json
from pathlib import Path
import uuid

import anyio
from bs4 import BeautifulSoup
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
            # tg.start_soon(_fetch_public_forecast, client)
            # tg.start_soon(_fetch_public_forecast_policy, client)
            # tg.start_soon(_fetch_severe_weather_outlook, client)
            # tg.start_soon(_fetch_public_forecast_tc_outlook, client)
            # tg.start_soon(_fetch_public_forecast_7_day, client)
            # tg.start_soon(_fetch_public_forecast_media, client)
            # tg.start_soon(_fetch_current_bulletin, client)
            # tg.start_soon(_fetch_severe_weather_warning, client)
            # tg.start_soon(_fetch_marine_waring, client)
            # tg.start_soon(_fetch_hight_seas_warning, client)


def _save_html(html: str, fp: Path):
    vmgd_directory = Path(ROOT_DIR / "data" / "vmgd")
    if fp.is_absolute():
        if not fp.is_relative_to(vmgd_directory):
            raise Exception(f"Bad path for saving html {fp}")
    else:
        fp = vmgd_directory / fp
    fp.write_text(html)


class VMGDResponseNotOK(Exception):
    """The response from VMGD was not OK."""

    def __init__(self, html: str, msg: str = None):
        self.msg = msg if msg else "The response from VMGD was not OK"
        fp = Path("errors" / str(uuid.uuid4()))
        logger.error(self.msg, response=str(fp))
        _save_html(html, fp)

    def __str__(self):
        return self.msg


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
            html = resp.text
            # _save_html(html, cached_page)
            cached_page.write_text(html)
        else:
            raise VMGDResponseNotOK(resp.text, f"Status not OK for {url=}")
    else:
        logger.info(f"Fetching page from cache {slug=}")
        html = cached_page.read_text()
    return html


async def _fetch_forecast(client: httpx.AsyncClient) -> None:
    """The main forecast page with daily temperature and humidity information and 6 hour
    interval resolution for weather condition, wind speed/direction.
    All information is encoded in a special `<script>` that contains a `var weathers`
    array which contains everything needed to reconstruct the information found in the
    forecast map.
    The specifics of how to decode the `weathers` array is found in the `xmlForecast.js`
    file that is on the page.
    """
    url = "/forecast-division"
    html = await _fetch(client, url)
    soup = BeautifulSoup(html, "html.parser")
    # Find weather script tag
    weathers_script = None
    for script in soup.find_all("script"):
        if script.text.strip().startswith("var weathers"):  # special value
            weathers_script = script
            break
    else:
        raise VMGDResponseNotOK("script containing `var weathers` not found")
    # Extract JSON data from script tag
    weathers_line = weathers_script.text.strip().split("\n", 1)[0]
    weathers_array_string = weathers_line.split(" = ", 1)[1].rsplit(";", 1)[0]
    weathers = json.loads(weathers_array_string)
    # TODO save weather data to persistent storage


# Public Forecast
#################


async def _fetch_public_forecast(client: httpx.AsyncClient) -> None:
    """The about page of the weather forecast section.

    TODO collect the text from table element with `<article class="item-page">` and
    hash it; store the hash and date collected in a directory so that only when the
    hash changes do we save a new page. This can also alert us to changes in the
    about page which may signal other important changes to how data is collected and
    reported in other forecast pages.
    """
    url = "/forecast-division/public-forecast"
    html = await _fetch(client, url)


async def _fetch_public_forecast_policy(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/public-forecast/forecast-policy"
    html = await _fetch(client, url)
    # TODO hash text contents of `<table class="forecastPublic">` to make a sanity
    # check that data presented or how data is processed is not changed. Only store
    # copies of the page that show a new hash value... I think. But maybe this is
    # the wrong html page downloaded as it appears same as `publice-forecast`


async def _fetch_severe_weather_outlook(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/public-forecast/severe-weather-outlook"
    html = await _fetch(client, url)
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="severeTable")
    # TODO assert table
    # TODO assert tablerows are 4
    # tr0 is date issues
    # tr1 is rainfall outlook
    # tr2 is inland wind outlook
    # tr3 is coastal wind outlook
    # any additional trX should be alerted and accounted for in future


async def _fetch_public_forecast_tc_outlook(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/public-forecast/tc-outlook"
    html = await _fetch(client, url)


async def _fetch_public_forecast_7_day(client: httpx.AsyncClient) -> None:
    """Simple weekly forecast for all locations containing daily low/high temperature,
    and weather condition summary.
    """
    url = "/forecast-division/public-forecast/7-day"
    html = await _fetch(client, url)
    soup = BeautifulSoup(html, "html.parser")
    # Extract data from individual tables for each location
    forecast_week = []
    for table in soup.article.find_all("table"):
        for count, tr in enumerate(table.find_all("tr")):
            if count == 0:
                location = tr.text.strip()
                continue
            date, forecast = tr.text.strip().split(" : ")
            summary = forecast.split(".", 1)[0]
            minTemp = forecast.split("Min:", 1)[1].split("&", 1)[0].strip()
            maxTemp = forecast.split("Max:", 1)[1].split("&", 1)[0].strip()
            forecast_week.append(
                dict(
                    location=location,
                    date=date,
                    summary=summary,
                    minTemp=minTemp,
                    maxTemp=maxTemp,
                )
            )


async def _fetch_public_forecast_media(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/public-forecast/media"
    html = await _fetch(client, url)
    # TODO extract data from `<table class="forecastPublic">` and download encoded `.png` file in `img` tag.


# Warnings
##########


async def _fetch_current_bulletin(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/warnings/current-bulletin"
    html = await _fetch(client, url)
    soup = BeautifulSoup(html, "html.parser")
    warning_div = soup.find("div", class_="foreWarning")
    if warning_div.text.lower().strip() == "there is no latest warning":
        # no warnings
        pass
    else:
        # TODO handle warnings
        pass


async def _fetch_severe_weather_warning(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/warnings/severe-weather-warning"
    html = await _fetch(client, url)
    # TODO extract data from table with class `marineFrontTabOne`


async def _fetch_marine_waring(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/warnings/marine-warning"
    html = await _fetch(client, url)
    # TODO extract data from table with class `marineFrontTabOne`


async def _fetch_hight_seas_warning(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/warnings/hight-seas-warning"
    html = await _fetch(client, url)
    # TODO extract data from `<article class="item-page">` and handle no warnings by text `NO CURRENT WARNING`
