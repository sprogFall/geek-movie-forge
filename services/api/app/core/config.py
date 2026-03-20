from functools import lru_cache
from os import getenv
from typing import Literal, Self

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
    db_backend: Literal["sqlite", "mysql"]
    sqlite_path: str
    mysql_host: str | None = None
    mysql_port: int = 3306
    mysql_user: str | None = None
    mysql_password: str | None = None
    mysql_database: str | None = None
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
        if self.db_backend == "sqlite":
            if not self.sqlite_path.strip():
                raise ValueError("SQLITE_PATH must not be blank when DB_BACKEND=sqlite")
        if self.db_backend == "mysql":
            required_fields = {
                "MYSQL_HOST": self.mysql_host,
                "MYSQL_USER": self.mysql_user,
                "MYSQL_PASSWORD": self.mysql_password,
                "MYSQL_DATABASE": self.mysql_database,
            }
            missing = [name for name, value in required_fields.items() if not value]
            if missing:
                raise ValueError(f"{missing[0]} is required when DB_BACKEND=mysql")
        if self.cors_allow_credentials and "*" in self.cors_allow_origins:
            raise ValueError("CORS_ALLOW_ORIGINS cannot include '*' when credentials are enabled")
        if self.api_max_request_bytes < 0:
            raise ValueError("API_MAX_REQUEST_BYTES must be >= 0")
        return self

    @property
    def database_url(self) -> str:
        if self.db_backend == "sqlite":
            return f"sqlite+pysqlite:///{self.sqlite_path}"
        return (
            "mysql+pymysql://"
            f"{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/"
            f"{self.mysql_database}"
        )


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
        db_backend=getenv("DB_BACKEND", "sqlite").strip().lower(),
        sqlite_path=getenv("SQLITE_PATH", ".data/geek_movie_forge.db"),
        mysql_host=getenv("MYSQL_HOST"),
        mysql_port=int(getenv("MYSQL_PORT", "3306")),
        mysql_user=getenv("MYSQL_USER"),
        mysql_password=getenv("MYSQL_PASSWORD"),
        mysql_database=getenv("MYSQL_DATABASE"),
        cors_allow_origins=cors_allow_origins,
        cors_allow_credentials=getenv("CORS_ALLOW_CREDENTIALS", "false").lower()
        in ("true", "1", "yes"),
        api_max_request_bytes=int(getenv("API_MAX_REQUEST_BYTES", "10485760")),
    )
