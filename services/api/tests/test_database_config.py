import os
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from services.api.app.core import config
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


def test_get_settings_escapes_special_characters_in_mysql_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_env(monkeypatch)
    monkeypatch.setenv("DB_BACKEND", "mysql")
    monkeypatch.setenv("MYSQL_HOST", "mysql.internal")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_USER", "gmf_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "pa@ss:word")
    monkeypatch.setenv("MYSQL_DATABASE", "gmf_db")
    get_settings.cache_clear()

    settings = get_settings()
    parsed = make_url(settings.database_url)

    assert "%40" in settings.database_url
    assert parsed.username == "gmf_user"
    assert parsed.password == "pa@ss:word"
    assert parsed.host == "mysql.internal"
    assert parsed.port == 3307
    assert parsed.database == "gmf_db"


def test_get_settings_exposes_safe_mysql_startup_log_description(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_database_env(monkeypatch)
    monkeypatch.setenv("DB_BACKEND", "mysql")
    monkeypatch.setenv("MYSQL_HOST", "mysql.internal")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_USER", "gmf_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "pa@ss:word")
    monkeypatch.setenv("MYSQL_DATABASE", "gmf_db")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.database_log_description == (
        "backend=mysql driver=mysql+pymysql host=mysql.internal "
        "port=3307 database=gmf_db user=gmf_user"
    )
    assert "pa@ss:word" not in settings.database_log_description


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


def test_load_dotenv_reads_project_root_env_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "repo"
    config_path = project_root / "services" / "api" / "app" / "core" / "config.py"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("# test config marker\n", encoding="utf-8")
    (project_root / "pyproject.toml").write_text("[project]\nname = 'gmf'\n", encoding="utf-8")
    (project_root / ".env").write_text("DB_BACKEND=mysql\n", encoding="utf-8")

    monkeypatch.delenv("DB_BACKEND", raising=False)
    config._load_dotenv(config_path)

    assert os.getenv("DB_BACKEND") == "mysql"
