from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from packages.db.models import CallLogRow
from packages.shared.contracts.call_logs import (
    CallLogListResponse,
    CallLogRecord,
    CallLogResponse,
    CallLogStatus,
    TokenUsage,
)
from services.api.app.services.errors import NotFoundServiceError


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


class InMemoryCallLogService:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

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
        token_usage: TokenUsage | None = None,
    ) -> CallLogResponse:
        created_at = datetime.now(UTC).isoformat()
        log_id = f"log_{uuid4().hex[:12]}"

        with self._session_factory() as session:
            session.add(
                CallLogRow(
                    log_id=log_id,
                    owner_id=owner_id,
                    provider_id=provider_id,
                    provider_name=provider_name,
                    model=model,
                    capability=capability,
                    request_body_summary=request_body_summary[:200],
                    response_status=response_status.value,
                    error_detail=error_detail,
                    duration_ms=duration_ms,
                    token_usage_json=token_usage.model_dump(mode="json") if token_usage else None,
                    created_at=created_at,
                )
            )
            session.commit()

        return CallLogResponse(
            log_id=log_id,
            provider_id=provider_id,
            provider_name=provider_name,
            model=model,
            capability=capability,
            request_body_summary=request_body_summary[:200],
            response_status=response_status,
            error_detail=error_detail,
            duration_ms=duration_ms,
            token_usage=token_usage,
            created_at=_parse_timestamp(created_at),
        )

    def list_logs(
        self,
        owner_id: str,
        *,
        provider_id: str | None = None,
        capability: str | None = None,
        status: CallLogStatus | None = None,
    ) -> CallLogListResponse:
        stmt = select(CallLogRow).where(CallLogRow.owner_id == owner_id)
        if provider_id is not None:
            stmt = stmt.where(CallLogRow.provider_id == provider_id)
        if capability is not None:
            stmt = stmt.where(CallLogRow.capability == capability)
        if status is not None:
            stmt = stmt.where(CallLogRow.response_status == status.value)
        stmt = stmt.order_by(desc(CallLogRow.created_at))

        with self._session_factory() as session:
            rows = session.scalars(stmt).all()
        return CallLogListResponse(items=[_to_response(row) for row in rows])

    def get_log(self, owner_id: str, log_id: str) -> CallLogResponse:
        with self._session_factory() as session:
            row = session.get(CallLogRow, log_id)
            if row is None or row.owner_id != owner_id:
                raise NotFoundServiceError("Call log not found")
            return _to_response(row)


def _to_response(row: CallLogRow) -> CallLogResponse:
    record = CallLogRecord(
        log_id=row.log_id,
        owner_id=row.owner_id,
        provider_id=row.provider_id,
        provider_name=row.provider_name,
        model=row.model,
        capability=row.capability,
        request_body_summary=row.request_body_summary,
        response_status=CallLogStatus(row.response_status),
        error_detail=row.error_detail,
        duration_ms=row.duration_ms,
        token_usage=TokenUsage.model_validate(row.token_usage_json) if row.token_usage_json else None,
        created_at=_parse_timestamp(row.created_at),
    )
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
        token_usage=record.token_usage,
        created_at=record.created_at,
    )
