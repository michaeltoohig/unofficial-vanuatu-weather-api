import json
from pathlib import Path

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
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


class Page(Base):
    __tablename__ = "page"
    
    id = Column(Integer, primary_key=True, index=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False)

    url = Column(String, nullable=False)
    _json_data = Column("json_data", String, nullable=False)

    @property
    def json_data(self):
        return json.loads(self._json_data)
    
    @json_data.setter
    def json_data(self, data):
        self._json_data = json.dumps(data)

    @property
    def slug(self):
        return self.url.rsplit("/", 1)[1]


class PageError(Base):
    __tablename__ = "page_error"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)

    url = Column(String, nullable=False)
    _file = Column("file", String, nullable=False)  # relative path or filename of html file that caused the error
    description = Column(String, nullable=False)

    @property
    def file(self):
        return Path(ROOT_DIR / "data" / "vmgd" / "errors", self._file)

    @file.setter
    def file(self, fp: Path):
        assert fp.relative_to(Path(ROOT_DIR / "data" / "vmgd" / "errors"))
        self._file = fp.name


# class Forecast(Base):
#     __tablename__ = "forecast"

#     id = Column(Integer, primary_key=True, index=True)
#     fetched_at = Column(DateTime(timezone=True), nullable=False, default=now)
#     issued_at = Column(DateTime(timezone=True), nullable=False)

#     location_id = Column(Integer, ForeignKey("location"), nullable=False)
#     location = relationship("Location")

#     # TODO


# class ForecastError(Base):
#     __tablename__ = "forecast_scraping_error"

#     id = Column(Integer, primary_key=True, index=True)
#     created_at = Column(DateTime(timezone=True), nullable=False, default=now)

#     description = Column(String, nullable=False)
#     url = Column(String, nullable=False)
#     file = Column(String)  # relative path or filename of html file that caused the error
