from functools import lru_cache
from os import getenv

from pydantic import BaseModel, field_validator

_DEFAULT_JWT_SECRET = "local-dev-jwt-secret-change-me-1234"


class Settings(BaseModel):
    app_name: str
    app_env: str
    jwt_secret: str
    jwt_expire_minutes: int

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=getenv("APP_NAME", "Geek Movie Forge API"),
        app_env=getenv("APP_ENV", "local"),
        jwt_secret=getenv("JWT_SECRET", _DEFAULT_JWT_SECRET),
        jwt_expire_minutes=int(getenv("JWT_EXPIRE_MINUTES", "1440")),
    )
