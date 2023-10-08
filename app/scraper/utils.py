# from datetime import datetime
from typing import TYPE_CHECKING
# import base64
from pathlib import Path

import httpx
from loguru import logger

from app import config
from app.scraper.exceptions import (
    FetchError,
    PageNotFoundError,
    PageUnavailableError,
)

if TYPE_CHECKING:
    from app.scraper.pages import PageMapping


def strip_html_text(text: str):
    return text.strip().replace("\n", " ").replace("\t", "").replace("\xa0", "")


def _save_html(html: str, fp: Path) -> None:
    vmgd_directory = Path(config.ROOT_DIR) / "data" / "vmgd"
    if fp.is_absolute():
        if not fp.is_relative_to(vmgd_directory):
            raise Exception(f"Bad path for saving html {fp}")
    else:
        fp = vmgd_directory / fp
        if not fp.parent.exists():
            fp.parent.mkdir(parents=True)
    fp.write_text(html)


# def _save_image(base64_string: str, fp: Path) -> None:
#     base64_data = base64_string.replace("data:image/png;base64,", "")
#     png_data = base64.b64decode(base64_data)
#     fp.write_bytes(png_data)


async def fetch(url: str) -> str:
    logger.info(f"Fetching {url}")

    async with httpx.AsyncClient(timeout=config.VMGD_TIMEOUT) as client:
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

    return resp.text


def check_cache(page: "PageMapping") -> str | None:
    # caching is for development only
    html = None
    cache_file = Path(config.ROOT_DIR / "data" / "vmgd" / page.slug)
    if cache_file.exists():
        logger.info(f"Fetching page from cache {page.slug=}")
        html = cache_file.read_text()
    return html, cache_file


async def fetch_page(page: "PageMapping"):
    cache_file = None
    if config.DEBUG and config.USE_PAGE_CACHE:
        html, cache_file = check_cache(page)
        if html:
            return html

    html = await fetch(page.url)

    if config.DEBUG and config.USE_PAGE_CACHE:
        cache_file.write_text(html)
    return html
