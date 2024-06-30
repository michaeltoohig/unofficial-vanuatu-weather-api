from datetime import datetime
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, synonym
from app.config import ROOT_DIR, VMGD_IMAGE_PATH

from app.database import Base

from app.utils.datetime import now, UTCDateTime
from app.utils.slugify import slugify

if TYPE_CHECKING:
    from app.scraper.pages import PagePath


class Session(Base):
    __tablename__ = "session"

    id = Column(Integer, primary_key=True, index=True)
    _name = Column("name", String, nullable=False)
    started_at = Column(UTCDateTime(), nullable=False, default=now)
    completed_at = Column(UTCDateTime())
    # error handling or record keeping in the session instead of a different table?
    # _errors = Column("errors", String)
    # count = Column(Integer)

    forecasts = relationship("ForecastDaily", back_populates="session")
    media = relationship("ForecastMedia", back_populates="session")
    images = relationship("Image", back_populates="session")
    weather_warnings = relationship("WeatherWarning", back_populates="session")

    def __init__(self, name: str):
        self._name = name

    fetched_at = synonym("started_at")


class Page(Base):
    __tablename__ = "page"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("session.id"), nullable=False)
    session = relationship("Session", lazy="joined")

    _path = Column("url", String, nullable=False)
    issued_at = Column(UTCDateTime(), nullable=False)
    _raw_data = Column("json_data", String, nullable=False)

    url = synonym("path")

    def __init__(
        self,
        path: "PagePath",
        raw_data: Any,
        session_id: int,
        issued_at: datetime,
    ):
        self._path = path.value
        self.raw_data = raw_data
        self.issued_at = issued_at
        self.session_id = session_id

    @property
    def raw_data(self):
        return json.loads(self._raw_data)

    @raw_data.setter
    def raw_data(self, data):
        self._raw_data = json.dumps(data)


class PageError(Base):
    __tablename__ = "page_error"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(UTCDateTime(), nullable=False, default=now)
    updated_at = Column(UTCDateTime())

    url = Column(String, nullable=False)
    _description = Column("description", String, nullable=False)
    exception = Column(String, nullable=False)
    html_hash = Column(String)
    _raw_data = Column("json_data", String)
    _errors = Column("errors", String)
    count = Column(Integer, default=1)

    def __init__(
        self,
        url: str,
        description: str,
        exception: str,
        html_hash: str,
        raw_data: Any | None = None,
        errors: Any | None = None,
    ):
        self.url = url
        self._description = description
        self.exception = exception
        self.html_hash = html_hash
        self.raw_data = raw_data
        self.errors = errors

    @staticmethod
    def get_html_directory() -> Path:
        return Path(ROOT_DIR / "data" / "vmgd" / "errors")

    @property
    def html_file(self):
        return self.get_html_directory() / self._file

    @property
    def raw_data(self):
        return json.loads(self._raw_data)

    @raw_data.setter
    def raw_data(self, obj):
        if obj is None:
            self._raw_data = None
        else:
            self._raw_data = json.dumps(obj)

    @property
    def errors(self):
        return json.loads(self._errors)

    @errors.setter
    def errors(self, obj):
        if obj is None:
            self._errors = None
        else:
            self._errors = json.dumps(obj)


class Location(Base):
    __tablename__ = "location"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(UTCDateTime(), nullable=False, default=now)
    updated_at = Column(UTCDateTime(), nullable=False, default=now)

    name = Column(String, nullable=False, unique=True)
    slug = Column(
        String, nullable=False
    )  # NOTE unique name will enforce a unique here for our small dataset
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    def __init__(self, name: str, latitude: float, longitude: float):
        self.name = name
        self.slug = slugify(name)
        self.latitude = latitude
        self.longitude = longitude

    def __repr__(self):
        return f"<Location({self.name})>"


class ForecastDaily(Base):
    __tablename__ = "forecast_daily"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("session.id"), nullable=False)
    session = relationship("Session", lazy="joined", back_populates="forecasts")

    location_id = Column(Integer, ForeignKey("location.id"), nullable=False)
    location = relationship("Location", lazy="joined")

    issued_at = Column(UTCDateTime(), nullable=False)
    date = Column(UTCDateTime(), nullable=False)
    summary = Column(String, nullable=False)
    minTemp = Column(Integer, nullable=False)
    maxTemp = Column(Integer, nullable=False)
    minHumi = Column(Integer, nullable=False)
    maxHumi = Column(Integer, nullable=False)
    # below values are available in 6 hour increments so we would have to calculate a daily average for each
    # windSpeed = Column(Integer, nullable=False)
    # windDir = Column(Float, nullable=False)


class ForecastMedia(Base):
    __tablename__ = "forecast_media"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("session.id"), nullable=False)
    session = relationship("Session", lazy="joined", back_populates="media")

    issued_at = Column(UTCDateTime(), nullable=False)
    summary = Column(String, nullable=False)


class Image(Base):
    __tablename__ = "image"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("session.id"), nullable=False)
    session = relationship("Session", lazy="joined", back_populates="images")

    issued_at = Column(UTCDateTime(), nullable=False)
    _server_filepath = Column("filepath", String, nullable=False, unique=True)

    def __init__(self, session_id: int, issued_at: datetime, filepath: Path) -> None:
        self.session_id = session_id
        self.issued_at = issued_at
        assert filepath.relative_to(
            VMGD_IMAGE_PATH
        ), "Image filepath is not subdirectory of root VMGD images directory"
        self._server_filepath = str(filepath.relative_to(VMGD_IMAGE_PATH))

    @property
    def filepath(self):
        return Path(VMGD_IMAGE_PATH) / self._server_filepath


class WeatherWarning(Base):
    __tablename__ = "warning"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("session.id"), nullable=False)
    session = relationship("Session", lazy="joined", back_populates="weather_warnings")

    issued_at = Column(UTCDateTime(), nullable=False)
    date = Column(UTCDateTime(), nullable=False)
    no_current_warning = Column(Boolean, nullable=False)
    body = Column(String)

    def __init__(
        self, session_id: int, issued_at: datetime, date: datetime, body: str = None
    ):
        self.session_id = session_id
        self.issued_at = issued_at
        self.date = date
        self.no_current_warning = body is None  # no body, no current warning; simple as
        self.body = body
