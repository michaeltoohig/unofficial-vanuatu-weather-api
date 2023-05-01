from datetime import datetime
import json
from typing import Any
from dataclasses import dataclass, field, fields

from fastapi import Request, status
from fastapi.responses import JSONResponse


@dataclass
class VmgdApiResponseMeta:
    issued: datetime
    fetched: datetime
    attribution: str = field(default="This default attribution to be in config later")


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
        data=data
    )


