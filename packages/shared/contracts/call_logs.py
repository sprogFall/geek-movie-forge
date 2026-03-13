from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CallLogStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class CallLogRecord(BaseModel):
    log_id: str
    owner_id: str
    provider_id: str
    provider_name: str
    model: str
    capability: str
    request_body_summary: str = Field(max_length=200)
    response_status: CallLogStatus
    error_detail: str | None = None
    duration_ms: int
    created_at: datetime


class CallLogResponse(BaseModel):
    log_id: str
    provider_id: str
    provider_name: str
    model: str
    capability: str
    request_body_summary: str
    response_status: CallLogStatus
    error_detail: str | None = None
    duration_ms: int
    created_at: datetime


class CallLogListResponse(BaseModel):
    items: list[CallLogResponse]
