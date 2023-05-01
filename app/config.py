import hashlib
import os
from pathlib import Path

from pydantic import BaseModel

from app.version import get_version_commit


ROOT_DIR = Path().parent.resolve()

VERSION_COMMIT = "dev"

try:
    from app._version import VERSION_COMMIT  # type: ignore
except ImportError:
    VERSION_COMMIT = get_version_commit()

VERSION = f"0.0.1+{VERSION_COMMIT}"
USER_AGENT = f"vmgd-api/{VERSION}"

# Force reloading cache when the CSS is updated
CSS_HASH = "none"
try:
    css_data = (ROOT_DIR / "app" / "static" / "css" / "main.css").read_bytes()
    CSS_HASH = hashlib.md5(css_data, usedforsecurity=False).hexdigest()
except FileNotFoundError:
    pass


class Config(BaseModel):
    domain: str = "localhost:8000"
    https: bool = False
    debug: bool = True
    sqlalchemy_database: str | None = None

    vmgd_base_url: str = "https://www.vmgd.gov.vu/vmgd/index.php"
    vmgd_attribution: str = "The data provided was collected on the `fetched` date provided from the Vanuatu Meteorology & Geo-Hazards Department website at https://vmgd.gov.vu/. This service should not be used by anyone for anything; always get up-to-date and accurate data from the VMGD website directly."


# def load_config() -> Config:
#     try:
#         return Config.parse_obj(
#             tomli.loads((ROOT_DIR / "data" / _CONFIG_FILE).read_text())
#         )
#     except FileNotFoundError:
#         raise ValueError(
#             f"Please run the configuration wizard, {_CONFIG_FILE} is missing"
#         )

# CONFIG = load_config()
CONFIG = Config()

DOMAIN = CONFIG.domain
_SCHEME = "https" if CONFIG.https else "http"
BASE_URL = f"{_SCHEME}://{DOMAIN}"

DEBUG = CONFIG.debug
DB_PATH = CONFIG.sqlalchemy_database or ROOT_DIR / "data" / "db.sqlite"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

VMGD_BASE_URL = CONFIG.vmgd_base_url
VMGD_ATTRIBUTION = CONFIG.vmgd_attribution