from datetime import datetime
from typing import Any
from dataclasses import dataclass, field

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.schemas import WeatherWarningResponse
from app.weather_warnings import get_latest_weather_warnings


@dataclass
class VmgdApiResponseMeta:
    issued: datetime
    fetched: datetime
    attribution: str = field(default=config.VMGD_ATTRIBUTION)


@dataclass
class VmgdApiResponse:
    meta: VmgdApiResponseMeta
    data: Any
    # warnings: list[WeatherWarningResponse] | None = None  # XXX seems unnecessary and messy to implement given the primary resource may be filtered by date then does that mmean we return filtered warnings also? Just dedicate an endpoint to warnings seems better IMO ATM.


async def render_vmgd_api_response(
    db_session: AsyncSession,
    request: Request,
    data: Any,
    *,
    issued: datetime,
    fetched: datetime,
    skip_warnings: bool = False,
) -> VmgdApiResponse:
    resp = VmgdApiResponse(
        meta=VmgdApiResponseMeta(
            issued=issued,
            fetched=fetched,
        ),
        data=data,
    )
    # if not skip_warnings:
    #     weather_warnings = await get_latest_weather_warnings(db_session)
    #     weather_warnings = list(filter(lambda ww: ww.no_current_warning is False, weather_warnings))
    #     import pdb; pdb.set_trace()  # fmt: skip
    #     # XXX does this work???
    #     warning_data = [
    #         WeatherWarningResponse(
    #             date=w.date,
    #             name=w.session._name,
    #             body=w.body,
    #         )
    #         for w in weather_warnings
    #     ]
    #     resp.warnings = warning_data
    return resp