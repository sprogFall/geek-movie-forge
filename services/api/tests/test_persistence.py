import json
from pathlib import Path

from packages.shared.contracts.providers import ProviderConfigCreateRequest
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
