import logging

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from services.api.app.middleware.api_logging import ApiLoggingMiddleware


def test_api_logging_middleware_rejects_oversize_request_body() -> None:
    app = FastAPI()
    app.add_middleware(ApiLoggingMiddleware, max_request_size_bytes=200)

    @app.post("/echo")
    async def echo(request: Request) -> dict:
        payload = await request.json()
        return {"received": payload}

    with TestClient(app) as client:
        response = client.post("/echo", json={"text": "a" * 2000})

    assert response.status_code == 413
    assert response.json()["detail"] == "Request body too large"
    assert response.headers.get("x-request-id")


def test_api_logging_middleware_sanitizes_sensitive_query_params(caplog) -> None:
    app = FastAPI()
    app.add_middleware(ApiLoggingMiddleware, max_request_size_bytes=1_000_000)

    @app.get("/ping")
    async def ping() -> dict:
        return {"ok": True}

    caplog.set_level(logging.INFO, logger="services.api.app.middleware.api_logging")

    with TestClient(app) as client:
        response = client.get("/ping?access_token=super-secret-value")

    assert response.status_code == 200
    assert "super-secret-value" not in caplog.text

