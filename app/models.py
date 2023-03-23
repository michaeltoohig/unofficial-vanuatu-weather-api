from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base
from app.utils.datetime import now


class Location(Base):
    __tablename__ = "location"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now)

    name = Column(String, nullable=False)
