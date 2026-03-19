import json
from pathlib import Path

from packages.shared.contracts.providers import (
    ProviderConfigCreateRequest,
    ProviderConfigUpdateRequest,
)
from services.api.app.core.store import JsonFileStore
from services.api.app.services.provider_service import InMemoryProviderService


def _custom_provider_names(service: InMemoryProviderService, owner_id: str) -> list[str]:
    return [item.name for item in service.list_providers(owner_id).items if not item.is_builtin]


def test_provider_data_survives_restart(tmp_path: Path) -> None:
    store = JsonFileStore(tmp_path)
    service = InMemoryProviderService(store=store)
    service.create_provider(
        "user_001",
        ProviderConfigCreateRequest(
            name="Persist Provider",
            base_url="https://example.com",
            api_key="test-key-123456",
            models=[{"model": "gpt-4", "capabilities": ["text"]}],
        ),
    )

    service2 = InMemoryProviderService(store=store)
    providers = service2.list_providers("user_001")
    assert len(providers.items) == 3
    assert _custom_provider_names(service2, "user_001") == ["Persist Provider"]


def test_store_none_does_not_persist(tmp_path: Path) -> None:
    service = InMemoryProviderService(store=None)
    service.create_provider(
        "user_001",
        ProviderConfigCreateRequest(
            name="Ephemeral",
            base_url="https://example.com",
            api_key="test-key-123456",
            models=[{"model": "gpt-4", "capabilities": ["text"]}],
        ),
    )
    assert list(tmp_path.iterdir()) == []


def test_corrupt_json_degrades_gracefully(tmp_path: Path) -> None:
    store = JsonFileStore(tmp_path)
    (tmp_path / "providers.json").write_text("{bad json", encoding="utf-8")

    service = InMemoryProviderService(store=store)
    providers = service.list_providers("user_001")
    assert len(providers.items) == 2
    assert all(item.is_builtin for item in providers.items)


def test_json_file_store_atomic_write(tmp_path: Path) -> None:
    store = JsonFileStore(tmp_path)
    store.save("test", {"key": "value"})

    target = tmp_path / "test.json"
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == {"key": "value"}
    assert not (tmp_path / "test.json.tmp").exists()


def test_delete_persists_removal(tmp_path: Path) -> None:
    store = JsonFileStore(tmp_path)
    service = InMemoryProviderService(store=store)
    resp = service.create_provider(
        "user_001",
        ProviderConfigCreateRequest(
            name="Deletable",
            base_url="https://example.com",
            api_key="test-key-123456",
            models=[{"model": "gpt-4", "capabilities": ["text"]}],
        ),
    )
    service.delete_provider("user_001", resp.provider_id)

    service2 = InMemoryProviderService(store=store)
    items = service2.list_providers("user_001").items
    assert len(items) == 2
    assert all(item.is_builtin for item in items)


def test_builtin_provider_api_key_refreshes_from_environment_after_restart(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = JsonFileStore(tmp_path)
    monkeypatch.setenv("VOLCENGINE_ARK_API_KEY", "first-secret-key")

    service = InMemoryProviderService(store=store)
    first = next(
        item
        for item in service.list_providers("user_001").items
        if item.is_builtin and item.adapter_type == "volcengine_ark"
    )
    assert first.api_key_masked.startswith("fir")

    monkeypatch.setenv("VOLCENGINE_ARK_API_KEY", "rotated-secret-key")
    service2 = InMemoryProviderService(store=store)
    second = next(
        item
        for item in service2.list_providers("user_001").items
        if item.is_builtin and item.adapter_type == "volcengine_ark"
    )
    assert second.api_key_masked.startswith("rot")


def test_builtin_provider_definition_refreshes_on_restart(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = JsonFileStore(tmp_path)
    monkeypatch.setenv("VOLCENGINE_ARK_API_KEY", "seedance-key-123456")

    service = InMemoryProviderService(store=store)
    builtin = next(
        item
        for item in service.list_providers("user_001").items
        if item.is_builtin and item.adapter_type == "volcengine_ark"
    )
    service.update_provider(
        "user_001",
        builtin.provider_id,
        payload=ProviderConfigUpdateRequest(
            name="Custom Ark Name",
            base_url="https://custom.example.com/api",
            api_key="manual-override-secret",
            models=[{"model": "custom-model", "capabilities": ["video"]}],
            routes={"video": {"path": "/custom/tasks", "timeout_seconds": 10.0}},
        ),
    )

    service2 = InMemoryProviderService(store=store)
    refreshed = next(
        item
        for item in service2.list_providers("user_001").items
        if item.is_builtin and item.adapter_type == "volcengine_ark"
    )
    assert refreshed.name == "Volcengine Ark"
    assert str(refreshed.base_url).rstrip("/") == "https://ark.cn-beijing.volces.com/api/v3"
    assert refreshed.models[0].model == "doubao-seedance-1-5-pro-251215"
    assert refreshed.routes.video.path == "/contents/generations/tasks"
    assert refreshed.api_key_masked.startswith("see")
