"""In-memory auth service with JWT and bcrypt."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from packages.shared.contracts.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from services.api.app.core.store import JsonFileStore
from services.api.app.services.errors import ConflictServiceError, UnauthorizedServiceError

_NAMESPACE = "auth"


class InMemoryAuthService:
    def __init__(
        self,
        jwt_secret: str,
        jwt_expire_minutes: int,
        *,
        store: JsonFileStore | None = None,
    ) -> None:
        self._jwt_secret = jwt_secret
        self._jwt_expire_minutes = jwt_expire_minutes
        # user_id -> {username, password_hash, created_at}
        self._users: dict[str, dict] = {}
        # username -> user_id (index for unique lookup)
        self._username_index: dict[str, str] = {}
        self._store = store
        self._load()

    def register(self, payload: RegisterRequest) -> TokenResponse:
        if payload.username in self._username_index:
            raise ConflictServiceError("Username already exists")

        user_id = f"user_{uuid.uuid4().hex[:12]}"
        password_hash = bcrypt.hashpw(
            payload.password.encode(), bcrypt.gensalt()
        ).decode()
        now = datetime.now(timezone.utc)

        self._users[user_id] = {
            "username": payload.username,
            "password_hash": password_hash,
            "created_at": now,
        }
        self._username_index[payload.username] = user_id
        self._persist()

        user = UserResponse(user_id=user_id, username=payload.username, created_at=now)
        token = self._create_token(user_id)
        return TokenResponse(access_token=token, user=user)

    def login(self, payload: LoginRequest) -> TokenResponse:
        user_id = self._username_index.get(payload.username)
        if user_id is None:
            raise UnauthorizedServiceError("Invalid username or password")

        record = self._users[user_id]
        if not bcrypt.checkpw(
            payload.password.encode(), record["password_hash"].encode()
        ):
            raise UnauthorizedServiceError("Invalid username or password")

        user = UserResponse(
            user_id=user_id,
            username=record["username"],
            created_at=record["created_at"],
        )
        token = self._create_token(user_id)
        return TokenResponse(access_token=token, user=user)

    def verify_token(self, token: str) -> UserResponse:
        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise UnauthorizedServiceError("Token has expired")
        except jwt.InvalidTokenError:
            raise UnauthorizedServiceError("Invalid token")

        user_id: str = payload.get("sub", "")
        record = self._users.get(user_id)
        if record is None:
            raise UnauthorizedServiceError("User not found")

        return UserResponse(
            user_id=user_id,
            username=record["username"],
            created_at=record["created_at"],
        )

    def _create_token(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(minutes=self._jwt_expire_minutes),
        }
        return jwt.encode(payload, self._jwt_secret, algorithm="HS256")

    def _persist(self) -> None:
        if self._store is None:
            return
        serialized_users = {}
        for uid, record in self._users.items():
            serialized_users[uid] = {
                "username": record["username"],
                "password_hash": record["password_hash"],
                "created_at": record["created_at"].isoformat()
                if isinstance(record["created_at"], datetime)
                else record["created_at"],
            }
        data = {
            "users": serialized_users,
            "username_index": self._username_index,
        }
        self._store.save(_NAMESPACE, data)

    def _load(self) -> None:
        if self._store is None:
            return
        data = self._store.load(_NAMESPACE)
        if data is None:
            return
        for uid, record in data.get("users", {}).items():
            try:
                created_at = record.get("created_at")
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                self._users[uid] = {
                    "username": record["username"],
                    "password_hash": record["password_hash"],
                    "created_at": created_at,
                }
            except Exception:
                logging.getLogger(__name__).warning(
                    "Skipping corrupt auth entry %s", uid
                )
        self._username_index = data.get("username_index", {})
