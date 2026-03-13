from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from packages.shared.contracts.call_logs import (
    CallLogListResponse,
    CallLogRecord,
    CallLogResponse,
    CallLogStatus,
)
from services.api.app.core.store import JsonFileStore
from services.api.app.services.errors import NotFoundServiceError

_NAMESPACE = "call_logs"


class InMemoryCallLogService:
    def __init__(self, *, store: JsonFileStore | None = None) -> None:
        self._logs: dict[str, CallLogRecord] = {}
        self._store = store
        self._load()

    def log_call(
        self,
        *,
        owner_id: str,
        provider_id: str,
        provider_name: str,
        model: str,
        capability: str,
        request_body_summary: str,
        response_status: CallLogStatus,
        error_detail: str | None = None,
        duration_ms: int,
    ) -> CallLogResponse:
        record = CallLogRecord(
            log_id=f"log_{uuid4().hex[:12]}",
            owner_id=owner_id,
            provider_id=provider_id,
            provider_name=provider_name,
            model=model,
            capability=capability,
            request_body_summary=request_body_summary[:200],
            response_status=response_status,
            error_detail=error_detail,
            duration_ms=duration_ms,
            created_at=datetime.now(UTC),
        )
        self._logs[record.log_id] = record
        self._persist()
        return self._to_response(record)

    def list_logs(
        self,
        owner_id: str,
        *,
        provider_id: str | None = None,
        capability: str | None = None,
        status: CallLogStatus | None = None,
    ) -> CallLogListResponse:
        items = [log for log in self._logs.values() if log.owner_id == owner_id]
        if provider_id is not None:
            items = [log for log in items if log.provider_id == provider_id]
        if capability is not None:
            items = [log for log in items if log.capability == capability]
        if status is not None:
            items = [log for log in items if log.response_status == status]
        items.sort(key=lambda log: log.created_at, reverse=True)
        return CallLogListResponse(items=[self._to_response(log) for log in items])

    def get_log(self, owner_id: str, log_id: str) -> CallLogResponse:
        record = self._logs.get(log_id)
        if record is None or record.owner_id != owner_id:
            raise NotFoundServiceError("Call log not found")
        return self._to_response(record)

    @staticmethod
    def _to_response(record: CallLogRecord) -> CallLogResponse:
        return CallLogResponse(
            log_id=record.log_id,
            provider_id=record.provider_id,
            provider_name=record.provider_name,
            model=record.model,
            capability=record.capability,
            request_body_summary=record.request_body_summary,
            response_status=record.response_status,
            error_detail=record.error_detail,
            duration_ms=record.duration_ms,
            created_at=record.created_at,
        )

    def _persist(self) -> None:
        if self._store is None:
            return
        data = {k: v.model_dump(mode="json") for k, v in self._logs.items()}
        self._store.save(_NAMESPACE, data)

    def _load(self) -> None:
        if self._store is None:
            return
        data = self._store.load(_NAMESPACE)
        if data is None:
            return
        for key, value in data.items():
            try:
                self._logs[key] = CallLogRecord(**value)
            except Exception:
                logging.getLogger(__name__).warning(
                    "Skipping corrupt call log entry %s", key
                )
