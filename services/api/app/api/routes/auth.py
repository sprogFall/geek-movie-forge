from fastapi import APIRouter, Depends, status

from packages.shared.contracts.auth import UserResponse
from services.api.app.dependencies.auth import get_auth_service, get_current_user
from services.api.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from services.api.app.services.auth_service import InMemoryAuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    auth_service: InMemoryAuthService = Depends(get_auth_service),
) -> TokenResponse:
    return auth_service.register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    auth_service: InMemoryAuthService = Depends(get_auth_service),
) -> TokenResponse:
    return auth_service.login(payload)


@router.get("/me", response_model=UserResponse)
async def me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user
