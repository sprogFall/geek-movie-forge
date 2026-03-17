from functools import lru_cache
from os import getenv
from typing import Self

from pydantic import BaseModel, field_validator, model_validator

_DEFAULT_JWT_SECRET = "local-dev-jwt-secret-change-me-1234"

_DEFAULT_LOCAL_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


class Settings(BaseModel):
    app_name: str
    app_env: str
    jwt_secret: str
    jwt_expire_minutes: int
    persist_enabled: bool
    persist_dir: str
    cors_allow_origins: list[str]
    cors_allow_credentials: bool
    api_max_request_bytes: int

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return value

    @model_validator(mode="after")
    def validate_security_defaults(self) -> Self:
        env = (self.app_env or "").strip().lower()
        if env not in ("local", "test") and self.jwt_secret == _DEFAULT_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET must be set to a non-default value when APP_ENV is not local/test"
            )
        if self.cors_allow_credentials and "*" in self.cors_allow_origins:
            raise ValueError("CORS_ALLOW_ORIGINS cannot include '*' when credentials are enabled")
        if self.api_max_request_bytes < 0:
            raise ValueError("API_MAX_REQUEST_BYTES must be >= 0")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_env = getenv("APP_ENV", "local")
    cors_allow_origins_raw = getenv("CORS_ALLOW_ORIGINS")
    if cors_allow_origins_raw is None:
        cors_allow_origins = list(_DEFAULT_LOCAL_CORS_ORIGINS) if app_env == "local" else []
    else:
        cors_allow_origins = [item.strip() for item in cors_allow_origins_raw.split(",") if item.strip()]
    return Settings(
        app_name=getenv("APP_NAME", "Geek Movie Forge API"),
        app_env=app_env,
        jwt_secret=getenv("JWT_SECRET", _DEFAULT_JWT_SECRET),
        jwt_expire_minutes=int(getenv("JWT_EXPIRE_MINUTES", "1440")),
        persist_enabled=getenv("PERSIST_ENABLED", "true" if app_env == "local" else "false").lower()
        in ("true", "1", "yes"),
        persist_dir=getenv("PERSIST_DIR", ".data"),
        cors_allow_origins=cors_allow_origins,
        cors_allow_credentials=getenv("CORS_ALLOW_CREDENTIALS", "false").lower()
        in ("true", "1", "yes"),
        api_max_request_bytes=int(getenv("API_MAX_REQUEST_BYTES", "10485760")),
    )
