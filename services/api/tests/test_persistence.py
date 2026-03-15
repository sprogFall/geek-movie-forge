import json
from pathlib import Path

from packages.shared.contracts.providers import ProviderConfigCreateRequest
from services.api.app.core.store import JsonFileStore
from services.api.app.services.provider_service import InMemoryProviderService


def _custom_provider_names(service: InMemoryProviderService, owner_id: str) -> list[str]:
    return [item.name for item in service.list_providers(owner_id).items if not item.is_builtin]


def test_provider_data_survives_restart(tmp_path: Path) -> None:
    """Create data with one store, then create a new service with the same store and verify."""
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

    # Simulate restart — new service instance, same store
    service2 = InMemoryProviderService(store=store)
    providers = service2.list_providers("user_001")
    assert len(providers.items) == 2
    assert _custom_provider_names(service2, "user_001") == ["Persist Provider"]


def test_store_none_does_not_persist(tmp_path: Path) -> None:
    """Without a store, nothing is written to disk."""
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
    # Nothing on disk at all
    assert list(tmp_path.iterdir()) == []


def test_corrupt_json_degrades_gracefully(tmp_path: Path) -> None:
    """If the JSON file is corrupt, the service starts with empty data."""
    store = JsonFileStore(tmp_path)

    # Write corrupt JSON
    (tmp_path / "providers.json").write_text("{bad json", encoding="utf-8")

    service = InMemoryProviderService(store=store)
    providers = service.list_providers("user_001")
    assert len(providers.items) == 1
    assert providers.items[0].is_builtin is True


def test_json_file_store_atomic_write(tmp_path: Path) -> None:
    """Verify that save writes a .tmp first, then renames to .json."""
    store = JsonFileStore(tmp_path)
    store.save("test", {"key": "value"})

    target = tmp_path / "test.json"
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == {"key": "value"}
    # No leftover tmp file
    assert not (tmp_path / "test.json.tmp").exists()


def test_delete_persists_removal(tmp_path: Path) -> None:
    """Deleted providers should not reappear after restart."""
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
    assert len(items) == 1
    assert items[0].is_builtin is True
