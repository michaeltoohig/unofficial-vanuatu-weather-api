from datetime import datetime
import json
from pathlib import Path
from tkinter import N
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.ext.hybrid import hybrid_property
from app.config import ROOT_DIR

from app.database import Base

# from app.scraper.sessions import SessionName
from app.utils.datetime import now

if TYPE_CHECKING:
    from app.scraper.pages import PagePath


class Session(Base):
    __tablename__ = "session"

    id = Column(Integer, primary_key=True, index=True)
    _name = Column("name", String, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, default=now)
    completed_at = Column(DateTime(timezone=True))
    # error handling or record keeping in the session instead of a different table?
    # _errors = Column("errors", String)
    # count = Column(Integer)

    def __init__(self, name: str):
        self._name = name

    fetched_at = synonym("started_at")

    # @hybrid_property
    # def name(self):
    #     return SessionName(self._name)

    # @name.setter
    # def name(self, value: SessionName):
    #     self._name = value.value

    # @name.expression
    # def name(cls):
    #     return cls._name


class Page(Base):
    __tablename__ = "page"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("session.id"), nullable=False)
    session = relationship("Session", lazy="joined")

    _path = Column("url", String, nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False)
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


# TODO save images collected from some pages
#
# class PageImage(Base):
#     __tablename__ = "page_image"

#     id = Column(Integer, primary_key=True, index=True)
#     fetched_at = Column(DateTime(timezone=True), nullable=False)
#     issued_at = Column(DateTime(timezone=True), nullable=False)

#     url = Column(String, nullable=False)
#     name = Column(String, nullable=False)
#     file_hash = Column(String, nullable=False)


class PageError(Base):
    __tablename__ = "page_error"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    updated_at = Column(DateTime(timezone=True))

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
        self._raw_data = json.dumps(obj)

    @property
    def errors(self):
        return json.loads(self._errors)

    @errors.setter
    def errors(self, obj):
        self._errors = json.dumps(obj)


class Location(Base):
    __tablename__ = "location"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now)

    name = Column(String, nullable=False, unique=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    def __init__(self, name: str, latitude: float, longitude: float):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude

    def __repr__(self):
        return f"<Location({self.name})>"


class ForecastDaily(Base):
    __tablename__ = "forecast_daily"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("session.id"), nullable=False)
    session = relationship("Session", lazy="joined", backref="forecasts")

    location_id = Column(Integer, ForeignKey("location.id"), nullable=False)
    location = relationship("Location", lazy="joined")

    issued_at = Column(DateTime(timezone=True), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    summary = Column(String, nullable=False)
    minTemp = Column(Integer, nullable=False)
    maxTemp = Column(Integer, nullable=False)
    minHumi = Column(Integer, nullable=False)
    maxHumi = Column(Integer, nullable=False)
    # below values are available in 6 hour increments so we would have to calculate a daily average for each
    # windSpeed = Column(Integer, nullable=False)
    # windDir = Column(Float, nullable=False)


# class Warnings(Base):
#     __tablename__ = "warnings"

#     id = Column(Integer, primary_key=True, index=True)
#     session_id = Column(Integer, ForeignKey("session.id"), nullable=False)
#     session = relationship("Session", lazy="joined")  #, backref="warnings")

#     category = Column(String, nullable=False)  # the slug of the page
    
#     issued_at = Column(DateTime(timezone=True), nullable=False)
#     date = Column(DateTime(timezone=True), nullable=False)
#     description = Column(String, nullable=False)
