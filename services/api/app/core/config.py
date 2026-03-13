from functools import lru_cache
from os import getenv

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = getenv("APP_NAME", "Geek Movie Forge API")
    app_env: str = getenv("APP_ENV", "local")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
