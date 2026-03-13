from fastapi.testclient import TestClient

from packages.provider_sdk.gateway import ProviderGateway
from packages.shared.contracts.generations import (
    ProviderMediaGenerationResult,
    ProviderTextGenerationResult,
)
from services.api.app.main import app
from services.api.app.services.generation_service import GenerationService
from services.api.tests.helpers import register_and_get_headers


class FakeProviderGateway(ProviderGateway):
    async def generate_image(self, provider, payload):
        return ProviderMediaGenerationResult(
            provider_request_id="img_req_001",
            outputs=[
                {
                    "index": 0,
                    "url": "https://cdn.example.com/generated/image-1.png",
                    "mime_type": "image/png",
                }
            ],
        )

    async def generate_video(self, provider, payload):
        return ProviderMediaGenerationResult(
            provider_request_id="vid_req_001",
            outputs=[
                {
                    "index": 0,
                    "url": "https://cdn.example.com/generated/video-1.mp4",
                    "mime_type": "video/mp4",
                }
            ],
        )

    async def generate_text(self, provider, payload):
        return ProviderTextGenerationResult(
            provider_request_id="txt_req_001",
            output_text="生成的文本结果。",
        )


class FailingProviderGateway(ProviderGateway):
    async def generate_image(self, provider, payload):
        raise RuntimeError("Connection refused")

    async def generate_video(self, provider, payload):
        raise RuntimeError("Connection refused")

    async def generate_text(self, provider, payload):
        raise RuntimeError("Connection refused")


def _create_provider(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/providers",
        json={
            "name": "Log Test Provider",
            "base_url": "https://provider.example.com/v1",
            "api_key": "super-secret-key",
            "models": [
                {"model": "forge-image-v1", "capabilities": ["image"]},
                {"model": "forge-text-v1", "capabilities": ["text"]},
            ],
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["provider_id"]


def test_image_generation_creates_success_call_log() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
            call_log_service=app.state.call_log_service,
        )
        provider_id = _create_provider(client, headers)

        client.post(
            "/api/v1/generations/images",
            json={
                "provider_id": provider_id,
                "model": "forge-image-v1",
                "count": 1,
                "prompt": "赛博朋克雨夜街道",
            },
            headers=headers,
        )

        logs_response = client.get("/api/v1/call-logs", headers=headers)

    assert logs_response.status_code == 200
    items = logs_response.json()["items"]
    assert len(items) == 1
    assert items[0]["response_status"] == "success"
    assert items[0]["capability"] == "image"
    assert items[0]["model"] == "forge-image-v1"
    assert items[0]["duration_ms"] >= 0


def test_gateway_error_creates_error_call_log() -> None:
    failing_gateway = FailingProviderGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=failing_gateway,
            call_log_service=app.state.call_log_service,
        )
        provider_id = _create_provider(client, headers)

        gen_response = client.post(
            "/api/v1/generations/images",
            json={
                "provider_id": provider_id,
                "model": "forge-image-v1",
                "count": 1,
                "prompt": "should fail",
            },
            headers=headers,
        )
        logs_response = client.get("/api/v1/call-logs", headers=headers)

    assert gen_response.status_code == 502
    items = logs_response.json()["items"]
    assert len(items) == 1
    assert items[0]["response_status"] == "error"
    assert "Connection refused" in items[0]["error_detail"]


def test_call_logs_filter_by_capability() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
            call_log_service=app.state.call_log_service,
        )
        provider_id = _create_provider(client, headers)

        # Generate image
        client.post(
            "/api/v1/generations/images",
            json={
                "provider_id": provider_id,
                "model": "forge-image-v1",
                "count": 1,
                "prompt": "image prompt",
            },
            headers=headers,
        )
        # Generate text
        client.post(
            "/api/v1/generations/texts",
            json={
                "provider_id": provider_id,
                "model": "forge-text-v1",
                "task_type": "script_writing",
                "source_text": "源文本",
                "prompt": "text prompt",
            },
            headers=headers,
        )

        all_logs = client.get("/api/v1/call-logs", headers=headers)
        image_logs = client.get(
            "/api/v1/call-logs", params={"capability": "image"}, headers=headers
        )
        text_logs = client.get(
            "/api/v1/call-logs", params={"capability": "text"}, headers=headers
        )

    assert len(all_logs.json()["items"]) == 2
    assert len(image_logs.json()["items"]) == 1
    assert image_logs.json()["items"][0]["capability"] == "image"
    assert len(text_logs.json()["items"]) == 1
    assert text_logs.json()["items"][0]["capability"] == "text"


def test_call_logs_filter_by_status() -> None:
    fake_gateway = FakeProviderGateway()
    failing_gateway = FailingProviderGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        provider_id = _create_provider(client, headers)

        # Success call
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
            call_log_service=app.state.call_log_service,
        )
        client.post(
            "/api/v1/generations/images",
            json={
                "provider_id": provider_id,
                "model": "forge-image-v1",
                "count": 1,
                "prompt": "success prompt",
            },
            headers=headers,
        )

        # Error call
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=failing_gateway,
            call_log_service=app.state.call_log_service,
        )
        client.post(
            "/api/v1/generations/images",
            json={
                "provider_id": provider_id,
                "model": "forge-image-v1",
                "count": 1,
                "prompt": "error prompt",
            },
            headers=headers,
        )

        success_logs = client.get(
            "/api/v1/call-logs", params={"status": "success"}, headers=headers
        )
        error_logs = client.get(
            "/api/v1/call-logs", params={"status": "error"}, headers=headers
        )

    assert len(success_logs.json()["items"]) == 1
    assert len(error_logs.json()["items"]) == 1


def test_call_logs_isolated_per_user() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        headers_a = register_and_get_headers(client, username="log_user_a")
        headers_b = register_and_get_headers(client, username="log_user_b")
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
            call_log_service=app.state.call_log_service,
        )

        # User A creates provider and generates
        provider_id = _create_provider(client, headers_a)
        client.post(
            "/api/v1/generations/images",
            json={
                "provider_id": provider_id,
                "model": "forge-image-v1",
                "count": 1,
                "prompt": "user A prompt",
            },
            headers=headers_a,
        )

        logs_a = client.get("/api/v1/call-logs", headers=headers_a)
        logs_b = client.get("/api/v1/call-logs", headers=headers_b)

    assert len(logs_a.json()["items"]) == 1
    assert len(logs_b.json()["items"]) == 0


def test_get_single_call_log() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
            call_log_service=app.state.call_log_service,
        )
        provider_id = _create_provider(client, headers)

        client.post(
            "/api/v1/generations/images",
            json={
                "provider_id": provider_id,
                "model": "forge-image-v1",
                "count": 1,
                "prompt": "单条查询",
            },
            headers=headers,
        )

        logs_response = client.get("/api/v1/call-logs", headers=headers)
        log_id = logs_response.json()["items"][0]["log_id"]

        detail_response = client.get(f"/api/v1/call-logs/{log_id}", headers=headers)

    assert detail_response.status_code == 200
    assert detail_response.json()["log_id"] == log_id


def test_get_nonexistent_call_log_returns_404() -> None:
    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        response = client.get("/api/v1/call-logs/log_nonexistent", headers=headers)

    assert response.status_code == 404
