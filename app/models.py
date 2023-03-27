from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

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


# class Forecast(Base):
#     __tablename__ = "forecast"

#     id = Column(Integer, primary_key=True, index=True)
#     fetched_at = Column(DateTime(timezone=True), nullable=False, default=now)
#     issued_at = Column(DateTime(timezone=True), nullable=False)

#     location_id = Column(Integer, ForeignKey("location"), nullable=False)
#     location = relationship("Location")

#     # TODO


class ForecastScrapingError(Base):
    __tablename__ = "forecast_scraping_error"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)

    description = Column(String, nullable=False)
    url = Column(String, nullable=False)
    file = Column(String)  # relative path or filename of html file that caused the error
