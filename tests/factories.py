from sqlalchemy import orm
import factory   # type: ignore

from app import models
from app.database import SessionLocal

_Session = orm.scoped_session(SessionLocal)


class BaseModelMeta:
    sqlalchemy_session = _Session
    sqlalchemy_session_persistence = "commit"


class LocationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseModelMeta):
        model = models.Location


class WeatherWarningFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta(BaseModelMeta):
        model = models.WeatherWarning
