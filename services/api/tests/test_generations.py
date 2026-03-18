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
    def __init__(self) -> None:
        self.last_image_payload = None
        self.last_video_payload = None
        self.last_text_payload = None

    async def generate_image(self, provider, payload):
        self.last_image_payload = {"provider": provider, "payload": payload}
        return ProviderMediaGenerationResult(
            provider_request_id="img_req_001",
            outputs=[
                {
                    "index": 0,
                    "url": "https://cdn.example.com/generated/image-1.png",
                    "mime_type": "image/png",
                },
                {
                    "index": 1,
                    "url": "https://cdn.example.com/generated/image-2.png",
                    "mime_type": "image/png",
                },
            ],
        )

    async def generate_video(self, provider, payload):
        self.last_video_payload = {"provider": provider, "payload": payload}
        return ProviderMediaGenerationResult(
            provider_request_id="vid_req_001",
            outputs=[
                {
                    "index": 0,
                    "url": "https://cdn.example.com/generated/video-1.mp4",
                    "mime_type": "video/mp4",
                    "cover_image_url": "https://cdn.example.com/generated/video-1-cover.png",
                    "duration_seconds": 8,
                }
            ],
        )

    async def generate_text(self, provider, payload):
        self.last_text_payload = {"provider": provider, "payload": payload}
        return ProviderTextGenerationResult(
            provider_request_id="txt_req_001",
            output_text="Opening shot: the ship cuts through the storm.",
        )


def _create_provider(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/providers",
        json={
            "name": "Generation Provider",
            "base_url": "https://provider.example.com/v1",
            "api_key": "super-secret-key",
            "models": [
                {"model": "forge-image-v1", "capabilities": ["image"]},
                {"model": "forge-video-v1", "capabilities": ["video"]},
                {"model": "forge-text-v1", "capabilities": ["text"]},
            ],
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["provider_id"]


def test_generate_image_and_save_assets() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
        )
        provider_id = _create_provider(client, headers)

        response = client.post(
            "/api/v1/generations/images",
            json={
                "provider_id": provider_id,
                "model": "forge-image-v1",
                "count": 2,
                "prompt": "A neon city street at night",
                "preset_prompt": "Movie poster composition",
                "save": {
                    "enabled": True,
                    "category": "storyboard",
                    "name_prefix": "opening-shot",
                    "tags": ["opening", "image"],
                },
                "options": {"size": "1024x1024"},
            },
            headers=headers,
        )
        list_assets_response = client.get(
            "/api/v1/assets",
            params={"asset_type": "image"},
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["provider_id"] == provider_id
    assert body["outputs"][0]["url"] == "https://cdn.example.com/generated/image-1.png"
    assert len(body["saved_assets"]) == 2
    assert body["saved_assets"][0]["category"] == "storyboard"
    assert fake_gateway.last_image_payload is not None
    assert (
        fake_gateway.last_image_payload["payload"].resolved_prompt
        == "Movie poster composition\nA neon city street at night"
    )
    assert list_assets_response.status_code == 200
    assert len(list_assets_response.json()["items"]) == 2


def test_generate_video_with_asset_materials_preserves_order() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
        )
        provider_id = _create_provider(client, headers)

        first_frame_asset = client.post(
            "/api/v1/assets",
            json={
                "asset_type": "image",
                "category": "reference",
                "name": "frame-1",
                "content_base64": "ZmFrZS1pbWFnZS0x",
                "mime_type": "image/png",
            },
            headers=headers,
        )
        last_frame_asset = client.post(
            "/api/v1/assets",
            json={
                "asset_type": "image",
                "category": "reference",
                "name": "frame-2",
                "content_url": "https://cdn.example.com/assets/frame-2.png",
            },
            headers=headers,
        )
        prompt_asset = client.post(
            "/api/v1/assets",
            json={
                "asset_type": "text",
                "category": "reference",
                "name": "scene",
                "content_text": "Heavy rain, low angle tracking shot, distant explosion.",
            },
            headers=headers,
        )

        response = client.post(
            "/api/v1/generations/videos",
            json={
                "provider_id": provider_id,
                "model": "forge-video-v1",
                "count": 1,
                "prompt": "The hero turns back toward the fire.",
                "preset_prompt": "Trailer style",
                "image_material_asset_ids": [
                    first_frame_asset.json()["asset_id"],
                    last_frame_asset.json()["asset_id"],
                ],
                "scene_prompt_asset_ids": [prompt_asset.json()["asset_id"]],
                "save": {
                    "enabled": True,
                    "category": "shots",
                    "name_prefix": "shot-01",
                },
                "options": {"duration_seconds": 8},
            },
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["outputs"][0]["url"] == "https://cdn.example.com/generated/video-1.mp4"
    assert body["saved_assets"][0]["asset_type"] == "video"
    assert fake_gateway.last_video_payload is not None
    payload = fake_gateway.last_video_payload["payload"]
    assert [item.kind for item in payload.image_materials] == ["base64", "url"]
    assert payload.image_materials[0].value == "data:image/png;base64,ZmFrZS1pbWFnZS0x"
    assert payload.image_materials[1].value == "https://cdn.example.com/assets/frame-2.png"
    assert payload.image_material_urls == ["https://cdn.example.com/assets/frame-2.png"]
    assert payload.image_material_base64 == ["data:image/png;base64,ZmFrZS1pbWFnZS0x"]
    assert payload.scene_prompt_texts == [
        "Heavy rain, low angle tracking shot, distant explosion."
    ]


def test_generate_video_allows_image_only_request() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
        )
        provider_id = _create_provider(client, headers)

        image_asset = client.post(
            "/api/v1/assets",
            json={
                "asset_type": "image",
                "category": "reference",
                "name": "frame-1",
                "content_url": "https://cdn.example.com/assets/frame-1.png",
            },
            headers=headers,
        )

        response = client.post(
            "/api/v1/generations/videos",
            json={
                "provider_id": provider_id,
                "model": "forge-video-v1",
                "count": 1,
                "image_material_asset_ids": [image_asset.json()["asset_id"]],
            },
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["resolved_prompt"] == ""
    assert fake_gateway.last_video_payload is not None
    payload = fake_gateway.last_video_payload["payload"]
    assert payload.resolved_prompt is None
    assert [item.value for item in payload.image_materials] == [
        "https://cdn.example.com/assets/frame-1.png"
    ]


def test_generate_text_and_query_saved_materials() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
        )
        provider_id = _create_provider(client, headers)

        response = client.post(
            "/api/v1/generations/texts",
            json={
                "provider_id": provider_id,
                "model": "forge-text-v1",
                "task_type": "script_writing",
                "source_text": "A pilot crash-lands on an abandoned moon.",
                "prompt": "Write a 60-second trailer script",
                "preset_prompt": "Tense pacing for a short cinematic teaser",
                "save": {
                    "enabled": True,
                    "category": "scripts",
                    "name_prefix": "teaser-script",
                },
            },
            headers=headers,
        )
        list_assets_response = client.get(
            "/api/v1/assets",
            params={"asset_type": "text", "category": "scripts"},
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["output_text"] == "Opening shot: the ship cuts through the storm."
    assert body["saved_assets"][0]["category"] == "scripts"
    assert fake_gateway.last_text_payload is not None
    assert fake_gateway.last_text_payload["payload"].task_type == "script_writing"
    assert list_assets_response.status_code == 200
    assert len(list_assets_response.json()["items"]) == 1
    assert list_assets_response.json()["items"][0]["content_text"] == body["output_text"]


def test_generate_rejects_model_without_required_capability() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
        )
        provider_id = _create_provider(client, headers)
        response = client.post(
            "/api/v1/generations/images",
            json={
                "provider_id": provider_id,
                "model": "forge-text-v1",
                "count": 1,
                "prompt": "This should be rejected",
            },
            headers=headers,
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Model does not support image generation"


def test_generate_rejects_provider_owned_by_other_user() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        owner_headers = register_and_get_headers(client, username="provider_owner")
        other_headers = register_and_get_headers(client, username="generation_user")
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
        )
        provider_id = _create_provider(client, owner_headers)

        response = client.post(
            "/api/v1/generations/images",
            json={
                "provider_id": provider_id,
                "model": "forge-image-v1",
                "count": 1,
                "prompt": "Other users should not access this provider",
            },
            headers=other_headers,
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Provider not found"


def test_generate_rejects_asset_material_owned_by_other_user() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        owner_headers = register_and_get_headers(client, username="asset_owner")
        other_headers = register_and_get_headers(client, username="video_user")
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
        )
        provider_id = _create_provider(client, other_headers)

        image_asset_response = client.post(
            "/api/v1/assets",
            json={
                "asset_type": "image",
                "category": "reference",
                "name": "private-reference",
                "content_url": "https://cdn.example.com/assets/private.png",
            },
            headers=owner_headers,
        )

        response = client.post(
            "/api/v1/generations/videos",
            json={
                "provider_id": provider_id,
                "model": "forge-video-v1",
                "count": 1,
                "prompt": "Using another user's asset should fail",
                "image_material_asset_ids": [image_asset_response.json()["asset_id"]],
            },
            headers=other_headers,
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"
