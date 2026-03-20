import pytest
from pydantic import ValidationError

from services.api.app.core.config import get_settings


def _clear_database_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DB_BACKEND",
        "SQLITE_PATH",
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_DATABASE",
    ):
        monkeypatch.delenv(key, raising=False)


def test_get_settings_defaults_to_sqlite_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_env(monkeypatch)
    get_settings.cache_clear()

    settings = get_settings()

    assert getattr(settings, "db_backend", None) == "sqlite"
    assert getattr(settings, "database_url", None) == "sqlite+pysqlite:///.data/geek_movie_forge.db"


def test_get_settings_builds_mysql_url_from_structured_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_env(monkeypatch)
    monkeypatch.setenv("DB_BACKEND", "mysql")
    monkeypatch.setenv("MYSQL_HOST", "mysql.internal")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_USER", "gmf_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "supersecret")
    monkeypatch.setenv("MYSQL_DATABASE", "gmf_db")
    get_settings.cache_clear()

    settings = get_settings()

    assert getattr(settings, "db_backend", None) == "mysql"
    assert (
        getattr(settings, "database_url", None)
        == "mysql+pymysql://gmf_user:supersecret@mysql.internal:3307/gmf_db"
    )


def test_get_settings_rejects_missing_mysql_connection_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_env(monkeypatch)
    monkeypatch.setenv("DB_BACKEND", "mysql")
    monkeypatch.setenv("MYSQL_USER", "gmf_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "supersecret")
    monkeypatch.setenv("MYSQL_DATABASE", "gmf_db")
    get_settings.cache_clear()

    with pytest.raises(ValidationError, match="MYSQL_HOST"):
        get_settings()
