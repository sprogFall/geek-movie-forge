from fastapi import APIRouter, Depends, Query

from packages.shared.contracts.auth import UserResponse
from packages.shared.contracts.call_logs import CallLogStatus
from services.api.app.dependencies.auth import get_current_user
from services.api.app.dependencies.services import get_call_log_service
from services.api.app.schemas.call_logs import CallLogListResponse, CallLogResponse
from services.api.app.services.call_log_service import InMemoryCallLogService

router = APIRouter(prefix="/api/v1/call-logs", tags=["call-logs"])


@router.get("", response_model=CallLogListResponse)
async def list_call_logs(
    provider_id: str | None = Query(default=None),
    capability: str | None = Query(default=None),
    status: CallLogStatus | None = Query(default=None),
    current_user: UserResponse = Depends(get_current_user),
    call_log_service: InMemoryCallLogService = Depends(get_call_log_service),
) -> CallLogListResponse:
    return call_log_service.list_logs(
        current_user.user_id,
        provider_id=provider_id,
        capability=capability,
        status=status,
    )


@router.get("/{log_id}", response_model=CallLogResponse)
async def get_call_log(
    log_id: str,
    current_user: UserResponse = Depends(get_current_user),
    call_log_service: InMemoryCallLogService = Depends(get_call_log_service),
) -> CallLogResponse:
    return call_log_service.get_log(current_user.user_id, log_id)
