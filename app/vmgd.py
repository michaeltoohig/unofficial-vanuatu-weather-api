from dataclasses import dataclass
from datetime import datetime
import enum
import json
from pathlib import Path
from typing import Any
import uuid

import anyio
from bs4 import BeautifulSoup
from cerberus import Validator
import httpx
from loguru import logger

from app import config, models
from app.database import AsyncSession, async_session
from app.pages import process_issued_at
from app.utils.datetime import now


BASE_URL = "https://www.vmgd.gov.vu/vmgd/index.php"
ProcessResult = tuple[datetime, Any]


def _save_html(html: str, fp: Path) -> Path:
    vmgd_directory = Path(config.ROOT_DIR) / "data" / "vmgd"
    if fp.is_absolute():
        if not fp.is_relative_to(vmgd_directory):
            raise Exception(f"Bad path for saving html {fp}")
    else:
        fp = vmgd_directory / fp
        if not fp.parent.exists():
            fp.parent.mkdir(parents=True)
    fp.write_text(html)
    return fp


class FetchError(Exception):
    def __init__(self, url: str, resp: httpx.Response | None = None) -> None:
        resp_part = ""
        if resp:
            filename = Path("errors") / str(uuid.uuid4())
            filepath = _save_html(resp.text, filename)
            resp_part = f", got HTTP {resp.status_code}, review HTML at {str(filename)}"
        message = f"Failed to fetch {url}{resp_part}"
        super().__init__(message)
        self.html = filepath
        self.resp = resp
        self.url = url


class PageUnavailableError(FetchError):
    pass


class PageNotFoundError(FetchError):
    pass


class ScrapingError(Exception):
    def __init__(self, html: str, data: Any | None = None, validation_errors: Any | None = None) -> None:
        filename = Path("errors") / str(uuid.uuid4())
        filepath = _save_html(html, filename)
        errors_part = ""
        if validation_errors:
            errors_part = f", got schema validation errors"
        message = f"Failed to scrape page, review HTML at {str(filename)}{errors_part}"
        super().__init__(message)
        self.html = filepath
        self.data = data
        self.validation_errors = validation_errors


class ScrapingNotFoundError(ScrapingError):
    pass


class ScrapingValidationError(ScrapingError):
    pass


class ScrapingIssuedAtError(ScrapingError):
    pass


class PageErrorTypeEnum(str, enum.Enum):
    TIMEOUT = "TIMEOUT"
    NOT_FOUND = "NOT_FOUND"
    UNAUHTORIZED = "UNAUTHORIZED"

    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    DATA_NOT_VALID = "DATA_NOT_VALID"
    ISSUED_NOT_FOUND = "ISSUED_NOT_FOUND"

    INTERNAL_ERROR = "INTERNAL_ERROR"


async def fetch(url: str) -> str:
    logger.info(f"Fetching {url}")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={
                "User-Agent": config.USER_AGENT,
            },
            follow_redirects=True,
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


process_forecast_schema = {
    "type": "list",
    "items": [
        {
            "type": "string",
            "name": "location",
        },
        {
            "type": "float",
            "name": "latitude",
        },
        {
            "type": "float",
            "name": "longitude",
        },
        {
            "type": "list",
            "name": "dates",
            "items": [{"type": "string"} for _ in range(8)],
        },
        {
            "type": "list",
            "name": "minTemperatures",
            "items": [{"type": "integer"} for _ in range(7)],
        },
        {
            "type": "list",
            "name": "maxTemperatures",
            "items": [{"type": "integer"} for _ in range(7)],
        },
        {
            "type": "list",
            "name": "minHumidity",
            "items": [{"type": "integer"} for _ in range(7)],
        },
        {
            "type": "list",
            "name": "maxHumidity",
            "items": [{"type": "integer"} for _ in range(7)],
        },
        {
            "type": "list",
            "name": "weatherConditions",
            "items": [{"type": "integer"} for _ in range(16)],
        },
        {
            "type": "list",
            "name": "windDirections",
            "items": [{"type": "float"} for _ in range(16)],
        },
        {
            "type": "list",
            "name": "windSpeeds",
            "items": [{"type": "integer"} for _ in range(16)],
        },
        {
            "type": "integer",
            "name": "dtFlag",
        },
        {
            "type": "string",
            "name": "currentDate",
        },
        {
            "type": "list",
            "name": "dateHours",
            "items": [{"type": "string"} for _ in range(16)],
        }
    ],
}


async def process_forecast(html: str) -> ProcessResult:
    """The main forecast page with daily temperature and humidity information and 6 hour
    interval resolution for weather condition, wind speed/direction.
    All information is encoded in a special `<script>` that contains a `var weathers`
    array which contains everything needed to reconstruct the information found in the
    forecast map.
    The specifics of how to decode the `weathers` array is found in the `xmlForecast.js`
    file that is on the page.
    """
    soup = BeautifulSoup(html, "html.parser")
    # Find JSON containing script tag
    weathers_script = None
    for script in soup.find_all("script"):
        if script.text.strip().startswith("var weathers"):  # special value
            weathers_script = script
            break
    else:
        raise ScrapingNotFoundError(html)

    # grab JSON data from script tag
    try:
        weathers_line = weathers_script.text.strip().split("\n", 1)[0]
        weathers_array_string = weathers_line.split(" = ", 1)[1].rsplit(";", 1)[0]
        weathers = json.loads(weathers_array_string)
        v = Validator(process_forecast_schema)
        if not v.validate(weathers):
            raise ScrapingValidationError(html, weathers, v.errors)
    except:
        raise ScrapingNotFoundError(html)

    # grab issued at datetime
    try:
        issued_str = soup.find("div", id="issueDate").text
        issued_at = process_issued_at(issued_str, "Forecast Issue Date:")
    except (IndexError, ValueError) as exc:
        raise ScrapingIssuedAtError(html)
    return issued_at, weathers


# Public Forecast
#################


async def process_public_forecast(html: str) -> ProcessResult:
    """The about page of the weather forecast section.

    TODO collect the text from table element with `<article class="item-page">` and
    hash it; store the hash and date collected in a directory so that only when the
    hash changes do we save a new page. This can also alert us to changes in the
    about page which may signal other important changes to how data is collected and
    reported in other forecast pages.
    """
    raise NotImplementedError


async def process_public_forecast_policy(html: str) -> ProcessResult:
    # TODO hash text contents of `<table class="forecastPublic">` to make a sanity
    # check that data presented or how data is processed is not changed. Only store
    # copies of the page that show a new hash value... I think. But maybe this is
    # the wrong html page downloaded as it appears same as `publice-forecast`
    raise NotImplementedError


async def process_severe_weather_outlook(html: str) -> ProcessResult:
    raise NotImplementedError
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="severeTable")
    # TODO assert table
    # TODO assert tablerows are 4
    # tr0 is date issues
    # tr1 is rainfall outlook
    # tr2 is inland wind outlook
    # tr3 is coastal wind outlook
    # any additional trX should be alerted and accounted for in future


async def process_public_forecast_tc_outlook(html: str) -> ProcessResult:
    raise NotImplementedError


process_public_forecast_7_day_schema = {
    "forecasts": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "location": {"type": "string", "empty": False},
                "date": {"type": "string", "empty": False},
                "summary": {"type": "string"},
                "minTemp": {"type": "integer", "coerce": int, "min": 0, "max": 50},
                "maxTemp": {"type": "integer", "coerce": int, "min": 0, "max": 50},
            }
        }
    }
}


async def process_public_forecast_7_day(html: str) -> ProcessResult:
    """Simple weekly forecast for all locations containing daily low/high temperature,
    and weather condition summary.
    """
    forecasts = []
    soup = BeautifulSoup(html, "html.parser")
    # grab data for each location from individual tables
    try:
        for table in soup.article.find_all("table"):
            for count, tr in enumerate(table.find_all("tr")):
                if count == 0:
                    location = tr.text.strip()
                    continue
                date, forecast = tr.text.strip().split(" : ")
                summary = forecast.split(".", 1)[0]
                minTemp = int(forecast.split("Min:", 1)[1].split("&", 1)[0].strip())
                maxTemp = int(forecast.split("Max:", 1)[1].split("&", 1)[0].strip())
                forecasts.append(
                    dict(
                        location=location,
                        date=date,
                        summary=summary,
                        minTemp=minTemp,
                        maxTemp=maxTemp,
                    )
                )
        v = Validator(process_public_forecast_7_day_schema)
        if not v.validate(dict(forecasts=forecasts)):
            raise ScrapingValidationError(html, forecasts, v.errors)
    except Exception as exc:
        raise ScrapingNotFoundError(html)

    # grab issued at datetime
    try:
        issued_str = soup.article.find("table").find_previous_sibling("strong").text.lower()
        issued_at = process_issued_at(issued_str, "Port Vila at")
    except (IndexError, ValueError) as exc:
        raise ScrapingIssuedAtError(html)
    return issued_at, forecasts


async def process_public_forecast_media(html: str) -> ProcessResult:
    # TODO extract data from `<table class="forecastPublic">` and download encoded `.png` file in `img` tag.
    raise NotImplementedError


# Warnings
##########


async def process_current_bulletin(html: str) -> ProcessResult:
    raise NotImplementedError
    soup = BeautifulSoup(html, "html.parser")
    warning_div = soup.find("div", class_="foreWarning")
    if warning_div.text.lower().strip() == "there is no latest warning":
        # no warnings
        pass
    else:
        # has warnings
        pass


async def process_severe_weather_warning(html: str) -> ProcessResult:
    # TODO extract data from table with class `marineFrontTabOne`
    raise NotImplementedError


async def process_marine_waring(html: str) -> ProcessResult:
    # TODO extract data from table with class `marineFrontTabOne`
    raise NotImplementedError


async def process_hight_seas_warning(html: str) -> ProcessResult:
    # TODO extract data from `<article class="item-page">` and handle no warnings by text `NO CURRENT WARNING`
    raise NotImplementedError


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


# TODO rename the functions that process the html since we are not fetching the data within these functions
pages_to_fetch = [
    PageToFetch("/forecast-division", process_forecast),
    # PageToFetch("/forecast-division/public-forecast", process_public_forecast),
    # PageToFetch(
    #     "/forecast-division/public-forecast/forecast-policy",
    #     process_public_forecast_policy,
    # ),
    # PageToFetch(
    #     "/forecast-division/public-forecast/severe-weather-outlook",
    #     process_severe_weather_outlook,
    # ),
    # PageToFetch(
    #     "/forecast-division/public-forecast/tc-outlook",
    #     process_public_forecast_tc_outlook,
    # ),
    PageToFetch(
        "/forecast-division/public-forecast/7-day", process_public_forecast_7_day
    ),
    # PageToFetch(
    #     "/forecast-division/public-forecast/media", process_public_forecast_media
    # ),
    # PageToFetch(
    #     "/forecast-division/warnings/current-bulletin", process_current_bulletin
    # ),
    # PageToFetch(
    #     "/forecast-division/warnings/severe-weather-warning",
    #     process_severe_weather_warning,
    # ),
    # PageToFetch("/forecast-division/warnings/marine-warning", process_marine_waring),
    # PageToFetch(
    #     "/forecast-division/warnings/hight-seas-warning", process_hight_seas_warning
    # ),
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


async def process_page(db_session: AsyncSession, ptf: PageToFetch):
    error = None
    fetched_at = now()
    try:
        html = await fetch_page(ptf)
    except httpx.TimeoutException:
        error = PageErrorTypeEnum.TIMEOUT
    except PageUnavailableError:
        error = PageErrorTypeEnum.UNAUHTORIZED
    except PageNotFoundError:
        error = PageErrorTypeEnum.NOT_FOUND
    except Exception as exc:
        logger.exception("Unexpected error fetching page: %s", str(exc))
        error = PageErrorTypeEnum.INTERNAL_ERROR
        page_error = models.PageError(url=ptf.url, description=str(e), file=e.html)
        db_session.add(page_error)
        return
        try:
            issued_at, data = await ptf.process(html)
        except ScrapingNotFoundError:
            error = PageErrorTypeEnum.DATA_NOT_FOUND
        except ScrapingValidationError:
            error = PageErrorTypeEnum.DATA_NOT_VALID
        except ScrapingIssuedAtError:
            error = PageErrorTypeEnum.ISSUED_NOT_FOUND
        except Exception as exc:
            logger.exception("Unexpected error processing page: %s", str(exc))
            error = PageErrorTypeEnum.INTERNAL_ERROR
        else:
            page = models.Page(url=ptf.url, issued_at=issued_at, raw_data=data, fetched_at=fetched_at)
            db_session.add(page)
    if error:
        page_error = models.PageError(url=ptf.url, description=error, file=Path("errors/test"))  # TODO get file from exception
        pass

async def process_all_pages(db_session) -> None:
    pass


async def run_process_all_pages() -> None:
    """CLI entrypoint."""
    # headers = {
    #     "User-Agent": config.USER_AGENT,
    # }
    # async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
    #     async with anyio.create_task_group() as tg:
    #         for ptf in pages_to_fetch:
    #             tg.start_soon(process_page, ptf)

    async with async_session() as db_session:
        async with anyio.create_task_group() as tg:
            for ptf in pages_to_fetch:
                tg.start_soon(process_page, db_session, ptf)
