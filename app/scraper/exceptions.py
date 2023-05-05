import enum
from typing import Any

import httpx

# currently this causes cyclic errors maybe better to merge all of this code into `pages`
# from app.vmgd.utils import _save_html


class FetchError(Exception):
    def __init__(self, url: str, resp: httpx.Response | None = None) -> None:
        resp_part = ""
        if resp:
            pass
            # filename = Path("errors") / str(uuid.uuid4())
            # filepath = _save_html(resp.text, filename)
            # resp_part = f", got HTTP {resp.status_code}, review HTML at {str(filename)}"
        message = f"Failed to fetch {url}{resp_part}"
        super().__init__(message)
        # self.html_filepath = filepath
        self.resp = resp
        self.url = url


class PageUnavailableError(FetchError):
    pass


class PageNotFoundError(FetchError):
    pass


class ScrapingError(Exception):
    def __init__(
        self, html: str, raw_data: Any | None = None, errors: Any | None = None
    ) -> None:
        # filename = Path("errors") / str(uuid.uuid4())
        # filepath = _save_html(html, filename)
        errors_part = ""
        if errors:
            errors_part = f", got schema validation errors"
        message = f"Failed to scrape page{errors_part}"
        super().__init__(message)
        self.html = html
        self.raw_data = raw_data
        self.errors = errors


class ScrapingNotFoundError(ScrapingError):
    pass


class ScrapingValidationError(ScrapingError):
    pass


class ScrapingIssuedAtError(ScrapingError):
    pass


# This may be better served from the `pages` file
class PageErrorTypeEnum(str, enum.Enum):
    TIMEOUT = "TIMEOUT"
    NOT_FOUND = "NOT_FOUND"
    UNAUHTORIZED = "UNAUTHORIZED"

    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    DATA_NOT_VALID = "DATA_NOT_VALID"
    ISSUED_NOT_FOUND = "ISSUED_NOT_FOUND"

    INTERNAL_ERROR = "INTERNAL_ERROR"
