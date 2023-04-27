from datetime import datetime
import json
from pathlib import Path
from tkinter import N
from typing import Any

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, synonym
from app.config import ROOT_DIR

from app.database import Base
from app.utils.datetime import now


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


# I am now hestitant to this idea after seeing it as unnecessary complexity
# a shared `fetched_at` value should be enough to query all forecast rows of a single *session*
# will rest and think about it
class Session(Base):
    __tablename__ = "session"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, default=now)
    completed_at = Column(DateTime(timezone=True))
    # error handling or record keeping in the session instead of a different table?
    # _errors = Column("errors", String)
    # count = Column(Integer)

    def __init__(self, name: str):
        self.name = name

    fetched_at = synonym("started_at")


class Page(Base):
    __tablename__ = "page"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("session.id"), nullable=False)
    fetched_at = Column(DateTime(timezone=True), nullable=False)  # found within session now
    issued_at = Column(DateTime(timezone=True), nullable=False)

    url = Column(String, nullable=False)
    _raw_data = Column("json_data", String, nullable=False)

    def __init__(
        self,
        url: str,
        raw_data: Any,
        session_id: int,
        issued_at: datetime,
        fetched_at: datetime | None = None,
    ):
        if fetched_at is None:
            fetched_at = now()
        self.url = url
        self.raw_data = raw_data
        self.issued_at = issued_at
        self.session_id = session_id
        self.fetched_at = fetched_at

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
    html_hash = Column(String, nullable=False)
    _raw_data = Column("json_data", String)
    _errors = Column("errors", String)
    count = Column(Integer, default=1)

    def __init__(
        self,
        url: str,
        description: str,
        html_hash: str,
        raw_data: Any | None = None,
        errors: Any | None = None,
    ):
        self.url = url
        self._description = description
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


class ForecastDaily(Base):
    __tablename__ = "forecast_daily"

    id = Column(Integer, primary_key=True, index=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False)

    session_id = Column(Integer, ForeignKey("session.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("location.id"), nullable=False)
    location = relationship("Location")

    date = Column(DateTime(timezone=True), nullable=False)
    summary = Column(String, nullable=False)
    minTemp = Column(Integer, nullable=False)
    maxTemp = Column(Integer, nullable=False)
    minHumi = Column(Integer, nullable=False)
    maxHumi = Column(Integer, nullable=False)
    # below values are available in 6 hour increments so we would have to calculate a daily average for each
    # windSpeed = Column(Integer, nullable=False)
    # windDir = Column(Float, nullable=False)

    

    # TODO


# class ForecastError(Base):
#     __tablename__ = "forecast_scraping_error"

#     id = Column(Integer, primary_key=True, index=True)
#     created_at = Column(DateTime(timezone=True), nullable=False, default=now)

#     description = Column(String, nullable=False)
#     url = Column(String, nullable=False)
#     file = Column(String)  # relative path or filename of html file that caused the error
