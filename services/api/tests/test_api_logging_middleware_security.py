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


def test_api_logging_middleware_sanitizes_sensitive_json_body(caplog) -> None:
    app = FastAPI()
    app.add_middleware(ApiLoggingMiddleware, max_request_size_bytes=1_000_000)

    @app.post("/echo")
    async def echo(request: Request) -> dict:
        payload = await request.json()
        return {"received": payload}

    caplog.set_level(logging.INFO, logger="services.api.app.middleware.api_logging")

    with TestClient(app) as client:
        response = client.post(
            "/echo",
            json={"password": "p@ssw0rd", "nested": {"access_token": "top-secret"}},
        )

    assert response.status_code == 200
    assert "p@ssw0rd" not in caplog.text
    assert "top-secret" not in caplog.text
    assert '"password":"***"' in caplog.text
    assert '"access_token":"***"' in caplog.text


def test_api_logging_middleware_logs_stacktrace_for_unhandled_errors(caplog) -> None:
    app = FastAPI()
    app.add_middleware(ApiLoggingMiddleware, max_request_size_bytes=1_000_000)

    @app.post("/boom")
    async def boom(request: Request) -> dict:
        _ = await request.json()
        raise RuntimeError("boom")

    caplog.set_level(logging.ERROR, logger="services.api.app.middleware.api_logging")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/boom", json={"access_token": "should-not-leak"})

    assert response.status_code == 500
    assert response.headers.get("x-request-id")
    assert "api_call_unhandled_error" in caplog.text
    assert "should-not-leak" not in caplog.text
    assert any(record.exc_info for record in caplog.records)


def test_api_logging_middleware_preserves_incoming_request_id() -> None:
    app = FastAPI()
    app.add_middleware(ApiLoggingMiddleware, max_request_size_bytes=1_000_000)

    @app.get("/ping")
    async def ping() -> dict:
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/ping", headers={"x-request-id": "trace_123-abc"})

    assert response.status_code == 200
    assert response.headers.get("x-request-id") == "trace_123-abc"
