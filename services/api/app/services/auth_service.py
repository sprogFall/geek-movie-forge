"""Auth service with JWT, bcrypt, and database persistence."""

import uuid
from datetime import UTC, datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from packages.db.models import UserRow
from packages.shared.contracts.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from services.api.app.services.errors import ConflictServiceError, UnauthorizedServiceError


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


class InMemoryAuthService:
    def __init__(
        self,
        jwt_secret: str,
        jwt_expire_minutes: int,
        *,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._jwt_secret = jwt_secret
        self._jwt_expire_minutes = jwt_expire_minutes
        self._session_factory = session_factory

    def register(self, payload: RegisterRequest) -> TokenResponse:
        with self._session_factory() as session:
            existing = session.scalar(select(UserRow).where(UserRow.username == payload.username))
            if existing is not None:
                raise ConflictServiceError("Username already exists")

            user_id = f"user_{uuid.uuid4().hex[:12]}"
            password_hash = bcrypt.hashpw(
                payload.password.encode(), bcrypt.gensalt()
            ).decode()
            created_at = datetime.now(UTC).isoformat()

            session.add(
                UserRow(
                    user_id=user_id,
                    username=payload.username,
                    password_hash=password_hash,
                    created_at=created_at,
                )
            )
            session.commit()

        user = UserResponse(
            user_id=user_id,
            username=payload.username,
            created_at=_parse_timestamp(created_at),
        )
        token = self._create_token(user_id)
        return TokenResponse(access_token=token, user=user)

    def login(self, payload: LoginRequest) -> TokenResponse:
        with self._session_factory() as session:
            record = session.scalar(select(UserRow).where(UserRow.username == payload.username))
            if record is None:
                raise UnauthorizedServiceError("Invalid username or password")
            if not bcrypt.checkpw(payload.password.encode(), record.password_hash.encode()):
                raise UnauthorizedServiceError("Invalid username or password")

            user = UserResponse(
                user_id=record.user_id,
                username=record.username,
                created_at=_parse_timestamp(record.created_at),
            )

        token = self._create_token(user.user_id)
        return TokenResponse(access_token=token, user=user)

    def verify_token(self, token: str) -> UserResponse:
        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise UnauthorizedServiceError("Token has expired")
        except jwt.InvalidTokenError:
            raise UnauthorizedServiceError("Invalid token")

        user_id: str = payload.get("sub", "")
        with self._session_factory() as session:
            record = session.get(UserRow, user_id)
            if record is None:
                raise UnauthorizedServiceError("User not found")

            return UserResponse(
                user_id=record.user_id,
                username=record.username,
                created_at=_parse_timestamp(record.created_at),
            )

    def _create_token(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(minutes=self._jwt_expire_minutes),
        }
        return jwt.encode(payload, self._jwt_secret, algorithm="HS256")
