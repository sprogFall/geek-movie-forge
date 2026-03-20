import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from packages.shared.contracts.assets import AssetCreateRequest
from packages.shared.contracts.auth import LoginRequest, RegisterRequest
from packages.shared.contracts.call_logs import CallLogStatus
from packages.shared.contracts.projects import ProjectCreateRequest
from packages.shared.contracts.providers import (
    ProviderConfigCreateRequest,
)
from packages.shared.contracts.tasks import TaskCreateRequest
from services.api.app.core.config import get_settings


def _load_fresh_app():
    import services.api.app.main as main_module

    get_settings.cache_clear()
    reloaded = importlib.reload(main_module)
    return reloaded.app


def test_domain_data_survives_restart_with_sqlite_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sqlite_path = tmp_path / "gmf-test.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))

    app = _load_fresh_app()
    try:
        with TestClient(app):
            token = app.state.auth_service.register(
                RegisterRequest(username="persist_user", password="secret123")
            )
            owner_id = token.user.user_id
            project = app.state.project_service.create_project(
                owner_id,
                ProjectCreateRequest(
                    title="Persistent Project",
                    summary="Keep this project",
                    platform="youtube",
                    aspect_ratio="16:9",
                ),
            )
            task = app.state.task_service.create_task(
                owner_id,
                TaskCreateRequest(
                    project_id=project.project_id,
                    title="Persistent Task",
                    source_text="Long source text",
                    platform="youtube",
                ),
            )
            provider = app.state.provider_service.create_provider(
                owner_id,
                ProviderConfigCreateRequest(
                    name="Persistent Provider",
                    base_url="https://example.com",
                    api_key="test-key-123456",
                    models=[{"model": "gpt-4", "capabilities": ["text"]}],
                ),
            )
            asset = app.state.asset_service.create_asset(
                owner_id,
                AssetCreateRequest(
                    asset_type="text",
                    category="script",
                    name="Persistent Asset",
                    content_text="Saved asset body",
                    tags=["persist"],
                    provider_id=provider.provider_id,
                    model="gpt-4",
                ),
            )
            log = app.state.call_log_service.log_call(
                owner_id=owner_id,
                provider_id=provider.provider_id,
                provider_name=provider.name,
                model="gpt-4",
                capability="text",
                request_body_summary="Persist this call log",
                response_status=CallLogStatus.SUCCESS,
                duration_ms=120,
            )
    except Exception as exc:  # pragma: no cover - exercised in current failing state
        pytest.fail(f"expected sqlite-backed app startup and first-write flow to succeed: {exc}")

    app = _load_fresh_app()
    with TestClient(app):
        try:
            login = app.state.auth_service.login(
                LoginRequest(username="persist_user", password="secret123")
            )
        except Exception as exc:  # pragma: no cover - exercised in current failing state
            pytest.fail(f"expected persisted user to be able to log in after restart: {exc}")

        assert login.user.user_id == owner_id
        assert [item.project_id for item in app.state.project_service.list_projects(owner_id).items] == [
            project.project_id
        ]
        assert [
            item.task_id
            for item in app.state.task_service.list_tasks(owner_id=owner_id).items
        ] == [task.task_id]
        assert [
            item.provider_id
            for item in app.state.provider_service.list_providers(owner_id).items
            if not item.is_builtin
        ] == [provider.provider_id]
        assert [
            item.asset_id
            for item in app.state.asset_service.list_assets(owner_id=owner_id).items
        ] == [asset.asset_id]
        assert [item.log_id for item in app.state.call_log_service.list_logs(owner_id).items] == [
            log.log_id
        ]

    assert sqlite_path.exists()
