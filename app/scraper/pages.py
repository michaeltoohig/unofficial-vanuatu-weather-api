from dataclasses import dataclass

from app.config import BASE_URL

import httpx
from loguru import logger

from app import config
from app.scraper.exceptions import FetchError, PageNotFoundError, PageUnavailableError


@dataclass
class PageMapping:
    relative_url: str
    process: callable
    scraper: callable
    # process_images: callable | None  # TODO decide how to handle pages that have images.
    # either a new process step to define for each page
    # or better yet return an 'images' key with the process results and treat that key special in the `process_page` function
    # the next level would be to save `PageImage` models as children of the Page model to keep them sorted and to prevent saving duplicate images store image hashes there, etc.
    # TODO figure it out next time to continue here

    # TODO add html: str to keey result of scraper
    # TODO add raw_results: Dict[str, Any] to keep results from process

    @property
    def url(self):
        return BASE_URL + self.relative_url

    @property
    def slug(self):
        return self.relative_url.rsplit("/", 1)[1]



