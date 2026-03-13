import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from services.api.app.core.config import get_settings
from services.api.app.main import app


def _register(client: TestClient, username: str = "testuser", password: str = "secret123"):
    return client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )


def _login(client: TestClient, username: str = "testuser", password: str = "secret123"):
    return client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )


def test_register_and_login_flow() -> None:
    with TestClient(app) as client:
        reg = _register(client)
        assert reg.status_code == 201
        body = reg.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["user"]["username"] == "testuser"
        assert body["user"]["user_id"].startswith("user_")

        login = _login(client)
        assert login.status_code == 200
        assert "access_token" in login.json()


def test_register_rejects_duplicate_username() -> None:
    with TestClient(app) as client:
        _register(client, "dup_user")
        dup = _register(client, "dup_user")
        assert dup.status_code == 409
        assert "already exists" in dup.json()["detail"]


def test_login_rejects_wrong_password() -> None:
    with TestClient(app) as client:
        _register(client, "login_user", "correct_pass")
        bad = _login(client, "login_user", "wrong_pass")
        assert bad.status_code == 401


def test_login_rejects_unknown_user() -> None:
    with TestClient(app) as client:
        bad = _login(client, "nonexistent", "whatever")
        assert bad.status_code == 401


def test_me_returns_user_info() -> None:
    with TestClient(app) as client:
        reg = _register(client, "me_user")
        token = reg.json()["access_token"]

        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["username"] == "me_user"


def test_me_rejects_missing_token() -> None:
    with TestClient(app) as client:
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 401


def test_me_rejects_invalid_token() -> None:
    with TestClient(app) as client:
        me = client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert me.status_code == 401


def test_protected_route_requires_auth() -> None:
    with TestClient(app) as client:
        res = client.get("/api/v1/providers")
        assert res.status_code == 401

        reg = _register(client, "auth_user")
        token = reg.json()["access_token"]

        res = client.get(
            "/api/v1/providers", headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200


def test_register_validates_input() -> None:
    with TestClient(app) as client:
        short_user = client.post(
            "/api/v1/auth/register", json={"username": "a", "password": "secret123"}
        )
        assert short_user.status_code == 422

        short_pass = client.post(
            "/api/v1/auth/register", json={"username": "gooduser", "password": "12"}
        )
        assert short_pass.status_code == 422


def test_get_settings_rejects_short_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "too-short-secret")
    get_settings.cache_clear()

    with pytest.raises(ValidationError, match="JWT_SECRET must be at least 32 characters"):
        get_settings()

    get_settings.cache_clear()
