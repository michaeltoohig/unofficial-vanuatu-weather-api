from datetime import datetime
from typing import Any, Type, TypeVar

from app.api.responses import (
    VmgdApiResponse,
    VmgdApiResponseMeta,
)


VmgdResponseT = TypeVar("VmgdResponseT", bound=VmgdApiResponse)


async def render_vmgd_api_response(
    data: Any,
    *,
    response_class: Type[VmgdResponseT],
    issued: datetime,
    fetched: datetime,
) -> VmgdApiResponse:
    resp = response_class(
        # remove microsecond for presentation purpose only
        meta=VmgdApiResponseMeta(
            issued=issued.replace(microsecond=0),
            fetched=fetched.replace(microsecond=0),
        ),
        data=data,
    )
    return resp
