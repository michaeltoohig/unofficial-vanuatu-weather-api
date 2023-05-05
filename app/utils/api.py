from datetime import datetime
from typing import Any
from dataclasses import dataclass, field

from app import config


@dataclass
class VmgdApiResponseMeta:
    issued: datetime
    fetched: datetime
    attribution: str = field(default=config.VMGD_ATTRIBUTION)


@dataclass
class VmgdApiResponse:
    meta: VmgdApiResponseMeta
    data: Any


def render_vmgd_api_response(
    data: Any, *, issued: datetime, fetched: datetime
) -> VmgdApiResponse:
    return VmgdApiResponse(
        meta=VmgdApiResponseMeta(
            issued=issued,
            fetched=fetched,
        ),
        data=data,
    )
