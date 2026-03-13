from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from packages.shared.contracts.auth import UserResponse
from services.api.app.services.auth_service import InMemoryAuthService

_bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(request: Request) -> InMemoryAuthService:
    return request.app.state.auth_service


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> UserResponse:
    from services.api.app.services.errors import UnauthorizedServiceError

    if credentials is None:
        raise UnauthorizedServiceError()
    auth_service: InMemoryAuthService = request.app.state.auth_service
    return auth_service.verify_token(credentials.credentials)
