import logging

from fastapi.testclient import TestClient

from services.api.app.main import app


def test_healthz_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_startup_logs_database_target(caplog) -> None:
    caplog.set_level(logging.INFO, logger="uvicorn.error")

    with TestClient(app):
        pass

    assert "Database connect target: backend=sqlite path=:memory:" in caplog.text
    assert "Database ready: backend=sqlite path=:memory:" in caplog.text
