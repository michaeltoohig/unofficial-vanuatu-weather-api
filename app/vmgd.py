from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import json
from pathlib import Path
import uuid

import anyio
from bs4 import BeautifulSoup
import httpx
from loguru import logger

from app import config, models
from app.database import async_session
from app.pages import extract_issued_at_datetime
from app.utils.datetime import now


BASE_URL = "https://www.vmgd.gov.vu/vmgd/index.php"


def _save_html(html: str, fp: Path):
    vmgd_directory = Path(config.ROOT_DIR / "data" / "vmgd")
    if fp.is_absolute():
        if not fp.is_relative_to(vmgd_directory):
            raise Exception(f"Bad path for saving html {fp}")
    else:
        fp = vmgd_directory / fp
    fp.write_text(html)


class FetchError(Exception):
    def __init__(self, url: str, resp: httpx.Response | None = None) -> None:
        resp_part = ""
        if resp:
            fp = Path("errors" / str(uuid.uuid4()))
            _save_html(resp.text, fp)
            resp_part = f", got HTTP {resp.status_code}, review HTML at {str(fp)}"
        message = f"Failed to fetch {url}{resp_part}"
        super().__init__(message)
        self.resp = resp
        self.url = url


class PageUnavailableError(FetchError):
    pass


class PageNotFoundError(FetchError)
    pass


async def fetch(url: str) -> str:
    logger.info(f"Fetching {url}")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={
                "User-Agent": config.USER_AGENT,
                "Accept": config.AP_CONTENT_TYPE,
            },
            params=params,
            follow_redirects=True,
            auth=None if disable_httpsig else auth,
        )

    if resp.status_code in [401, 403]:
        raise PageUnavailableError(url, resp)
    elif resp.status_code == 404:
        raise PageNotFoundError(url, resp)

    try:
        resp.raise_for_status()
    except httpx.HTTPError as http_error:
        raise FetchError(url, resp) from http_error

    return resp.html


async def fetch_page(db_session: AsyncSession, page: PageToFetch) -> str:
    url = BASE_URL + page.url
    cached_page = Path(config.ROOT_DIR / "data" / "vmgd" / page.slug)
    if cached_page.exists():
        logger.info(f"Fetching page from cache {page.slug=}")
        html = cached_page.read_text()
    else:
        html = await fetch(url)
        cached_page.write_text(html)
    return html

    # existing_actor = (
    #     await db_session.scalars(
    #         select(models.Actor).where(
    #             models.Actor.ap_id == actor_id,
    #         )
    #     )
    # ).one_or_none()
    # if existing_actor:
    #     if existing_actor.is_deleted:
    #         raise ap.ObjectNotFoundError(f"{actor_id} was deleted")



# async def fetch_page(client: httpx.AsyncClient, page: models.Page) -> httpx.Response:
#     """Fetch the web page.
#     Currently we store a cached copy for development purposes but in the future I will
#     keep the `/data/vmgd` directory to store pages that fail scraping for debugging.
#     """
#     url = BASE_URL + page.url
#     cached_page = Path(config.ROOT_DIR / "data" / "vmgd" / page.slug)
#     if not cached_page.exists():
#         logger.info(f"Fetching {url=}")
#         # TODO retry httpx.ConnectError
#         resp = await client.get(url)
#         if resp.status_code == httpx.codes.OK:
#             html = resp.text
#             # _save_html(html, cached_page)
#             cached_page.write_text(html)
#             # async with async_session() as db_session:
#             #     db_session.add(page)
#         else:
#             raise VMGDResponseNotOK(resp.text, f"Status not OK for {url=}")
#     else:
#         logger.info(f"Fetching page from cache {page.slug=}")
#         html = cached_page.read_text()
#     return html


async def _fetch_forecast(client: httpx.AsyncClient) -> None:
    """The main forecast page with daily temperature and humidity information and 6 hour
    interval resolution for weather condition, wind speed/direction.
    All information is encoded in a special `<script>` that contains a `var weathers`
    array which contains everything needed to reconstruct the information found in the
    forecast map.
    The specifics of how to decode the `weathers` array is found in the `xmlForecast.js`
    file that is on the page.
    """
    # page = models.Page(url=)
    html = await fetch_page(client, page)
    page.fetched_at = now()
    soup = BeautifulSoup(html, "html.parser")

    # Find weather script tag
    weathers_script = None
    for script in soup.find_all("script"):
        if script.text.strip().startswith("var weathers"):  # special value
            weathers_script = script
            break
    else:
        raise VMGDResponseNotOK("script containing `var weathers` not found")

    # grab JSON data from script tag
    weathers_line = weathers_script.text.strip().split("\n", 1)[0]
    weathers_array_string = weathers_line.split(" = ", 1)[1].rsplit(";", 1)[0]
    weathers = json.loads(weathers_array_string)
    # TODO assert schema of weathers then save to storage
    page.json_data = weathers

    # grab issue date
    issued_str = soup.find("div", id="issueDate").text.lower().strip()
    # issued_date_str, issued_time_str = issued_str.split("date: ", 1)[1].split("(utc time")[0].strip().split(" at ")
    # issued_date_str = issued_date_str[:6] + issued_date_str[8:]  # remove 'st', 'nd', 'rd', 'th'
    # issued_at = datetime.strptime(issued_date_str, "%a %d %B, %Y")
    # issued_at = datetime.combine(date=issued_at.date(), time=datetime.strptime(issued_time_str, "%H:%M").time())
    # tz_vu = timezone(timedelta(hours=11))
    # issued_at = issued_at.replace(tzinfo=tz_vu)
    # issued_at_utc = issued_at.astimezone(timezone.utc)
    issued_at = extract_issued_at_datetime(issued_str)
    page.issued_at = issued_at

    async with async_session() as db_session:
        db_session.add(page)
        await db_session.commit()


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
    html = await fetch_page(client, url)


async def _fetch_public_forecast_policy(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/public-forecast/forecast-policy"
    html = await fetch_page(client, url)
    # TODO hash text contents of `<table class="forecastPublic">` to make a sanity
    # check that data presented or how data is processed is not changed. Only store
    # copies of the page that show a new hash value... I think. But maybe this is
    # the wrong html page downloaded as it appears same as `publice-forecast`


async def _fetch_severe_weather_outlook(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/public-forecast/severe-weather-outlook"
    html = await fetch_page(client, url)
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
    html = await fetch_page(client, url)


async def _fetch_public_forecast_7_day(client: httpx.AsyncClient) -> None:
    """Simple weekly forecast for all locations containing daily low/high temperature,
    and weather condition summary.
    """
    page = models.Page(url="/forecast-division/public-forecast/7-day")
    html = await fetch_page(client, page)
    page.fetched_at = now()
    soup = BeautifulSoup(html, "html.parser")
    
    # grab data for each location from individual tables
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
    page.json_data = forecast_week

    # grab issued at date time
    issued_str = soup.article.find("table").find_previous_sibling("strong").text.lower()
    # examples include "Mon 27th March, 2023 at 15:02 (UTC Time:04:02)" or "Tue 28th March, 2023 at 16:05 (UTC Time:05:05)"
    issued_str = issued_str.split("(utc time",  1)[0].split("port vila at")[1].strip()
    issued_at = extract_issued_at_datetime(issued_str)
    # issued_date_str, issued_time_str = issued_str.split(" at ")
    # issued_date_str = issued_date_str[:6] + issued_date_str[8:]  # remove 'st', 'nd', 'rd', 'th'
    # issued_at = datetime.strptime(issued_date_str, "%a %d %B, %Y")
    # issued_at = datetime.combine(date=issued_at.date(), time=datetime.strptime(issued_time_str, "%H:%M").time())
    # tz_vu = timezone(timedelta(hours=11))
    # issued_at = issued_at.replace(tzinfo=tz_vu)
    # issued_at_utc = issued_at.astimezone(timezone.utc)
    page.issued_at = issued_at

    # save page
    async with async_session() as db_session:
        db_session.add(page)
        await db_session.commit()


async def _fetch_public_forecast_media(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/public-forecast/media"
    html = await fetch_page(client, url)
    # TODO extract data from `<table class="forecastPublic">` and download encoded `.png` file in `img` tag.


# Warnings
##########


async def _fetch_current_bulletin(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/warnings/current-bulletin"
    html = await fetch_page(client, url)
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
    html = await fetch_page(client, url)
    # TODO extract data from table with class `marineFrontTabOne`


async def _fetch_marine_waring(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/warnings/marine-warning"
    html = await fetch_page(client, url)
    # TODO extract data from table with class `marineFrontTabOne`


async def _fetch_hight_seas_warning(client: httpx.AsyncClient) -> None:
    url = "/forecast-division/warnings/hight-seas-warning"
    html = await fetch_page(client, url)
    # TODO extract data from `<article class="item-page">` and handle no warnings by text `NO CURRENT WARNING`


@dataclass
class PageToFetch:
    relative_url: str
    process: callable

    @property
    def url(self):
        return BASE_URL + self.relative_url

    @property
    def slug(self):
        return self.relative_url.rsplit("/", 1)[1]

# TODO complete URLs here
# TODO rewrite each function to handle the html and not to fetch the url
# TODO rename the functions that process the html since we are not fetching the data within these functions
pages_to_fetch = [
    PageToFetch("/forecast-division", _fetch_forecast),
    PageToFetch("/forecast-division/public-forecast", _fetch_public_forecast),
    PageToFetch("/forecast-division/public-forecast/forecast-policy", _fetch_public_forecast_policy),
    PageToFetch("/forecast-division/public-forecast/severe-weather-outlook", _fetch_severe_weather_outlook),
    PageToFetch("/forecast-division/public-forecast/tc-outlook", _fetch_public_forecast_tc_outlook),
    PageToFetch("", _fetch_public_forecast_7_day),
    PageToFetch("", _fetch_public_forecast_media),
    PageToFetch("", _fetch_current_bulletin),
    PageToFetch("", _fetch_severe_weather_warning),
    PageToFetch("", _fetch_marine_waring),
    PageToFetch("", _fetch_hight_seas_warning),
]


async def fetch_page(page: PageToFetch):
    cached_page = Path(config.ROOT_DIR / "data" / "vmgd" / page.slug)
    if cached_page.exists():
        logger.info(f"Fetching page from cache {page.slug=}")
        html = cached_page.read_text()
    else:
        html = await fetch(page.url)
        cached_page.write_text(html)
    return html


async def process_pages(page: PageToFetch):
    # TODO add client to `fetch_page` for httpx.AsyncClient - or not and forego slight benefits
    html = await fetch_page(page.url)
    data = await page.process(html)
    # TODO handle the page data (ex. save to database page table)


async def fetch_all_pages(db_session) -> None:
    pass


async def run_fetch_all_pages() -> None:
    """CLI entrypoint."""
    # TODO
    headers = {
        "User-Agent": config.USER_AGENT,
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        async with anyio.create_task_group() as tg:
            for ptf in pages_to_fetch:
                tg.start_soon(process_page(ptf))
