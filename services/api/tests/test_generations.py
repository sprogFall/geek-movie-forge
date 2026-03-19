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
        duration_seconds = payload.options.get("duration_seconds") or payload.options.get("duration")
        return ProviderMediaGenerationResult(
            provider_request_id="vid_req_001",
            outputs=[
                {
                    "index": 0,
                    "url": "https://cdn.example.com/generated/video-1.mp4",
                    "mime_type": "video/mp4",
                    "cover_image_url": "https://cdn.example.com/generated/video-1-cover.png",
                    "duration_seconds": duration_seconds or 8,
                }
            ],
            usage={"input_tokens": 120, "output_tokens": 45, "total_tokens": 165},
        )

    async def generate_text(self, provider, payload):
        self.last_text_payload = {"provider": provider, "payload": payload}
        if payload.task_type == "video_segmentation_plan":
            return ProviderTextGenerationResult(
                provider_request_id="txt_plan_001",
                output_text=(
                    '{"segments":['
                    '{"title":"开场钩子","visual_prompt":"夜色城市俯拍，霓虹闪烁","narration_text":"雨夜里，主角独自穿过空旷街头。"},'
                    '{"title":"冲突升级","visual_prompt":"镜头快速推进，敌人逼近","narration_text":"警报骤然响起，身后的追兵越来越近。"},'
                    '{"title":"情绪收束","visual_prompt":"慢镜头定格，人物回头","narration_text":"他终于停下脚步，决定直面这场追逐。"}'
                    ']}'
                ),
                usage={"input_tokens": 80, "output_tokens": 50, "total_tokens": 130},
            )
        return ProviderTextGenerationResult(
            provider_request_id="txt_req_001",
            output_text="开场镜头：飞船劈开风暴，朝着失落海域疾驰。",
            usage={"input_tokens": 60, "output_tokens": 32, "total_tokens": 92},
        )


class PartialFailVideoGateway(FakeProviderGateway):
    async def generate_video(self, provider, payload):
        self.last_video_payload = {"provider": provider, "payload": payload}
        if "冲突升级" in (payload.prompt or ""):
            raise RuntimeError("second segment failed")
        return await super().generate_video(provider, payload)


class RecordingVideoGateway(FakeProviderGateway):
    def __init__(self) -> None:
        super().__init__()
        self.video_payloads = []

    async def generate_video(self, provider, payload):
        self.last_video_payload = {"provider": provider, "payload": payload}
        self.video_payloads.append({"provider": provider, "payload": payload})
        return await super().generate_video(provider, payload)


def _create_provider(
    client: TestClient,
    headers: dict[str, str],
    *,
    adapter_type: str = "generic_json",
) -> str:
    response = client.post(
        "/api/v1/providers",
        json={
            "name": "Generation Provider",
            "base_url": "https://provider.example.com/v1",
            "api_key": "super-secret-key",
            "adapter_type": adapter_type,
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
    assert body["output_text"] == "开场镜头：飞船劈开风暴，朝着失落海域疾驰。"
    assert body["saved_assets"][0]["category"] == "scripts"
    assert fake_gateway.last_text_payload is not None
    assert fake_gateway.last_text_payload["payload"].task_type == "script_writing"
    assert "只输出简体中文结果" in fake_gateway.last_text_payload["payload"].resolved_prompt
    assert list_assets_response.status_code == 200
    assert len(list_assets_response.json()["items"]) == 1
    assert list_assets_response.json()["items"][0]["content_text"] == body["output_text"]


def test_plan_multi_video_returns_ai_segment_plan() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
        )
        provider_id = _create_provider(client, headers)

        prompt_asset = client.post(
            "/api/v1/assets",
            json={
                "asset_type": "text",
                "category": "reference",
                "name": "scene",
                "content_text": "城市追逐，节奏紧张，结尾反转。",
            },
            headers=headers,
        )

        response = client.post(
            "/api/v1/generations/videos/plan",
            json={
                "provider_id": provider_id,
                "model": "forge-text-v1",
                "prompt": "做一个 26 秒的中文悬疑短视频",
                "total_duration_seconds": 26,
                "segment_duration_seconds": 10,
                "scene_prompt_asset_ids": [prompt_asset.json()["asset_id"]],
            },
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["segment_count"] == 3
    assert [item["duration_seconds"] for item in body["segments"]] == [10, 10, 6]
    assert body["segments"][0]["title"] == "开场钩子"
    assert body["usage"]["total_tokens"] == 130
    assert fake_gateway.last_text_payload is not None
    assert fake_gateway.last_text_payload["payload"].task_type == "video_segmentation_plan"
    assert "只能输出 JSON 对象" in fake_gateway.last_text_payload["payload"].resolved_prompt


def test_generate_multi_video_returns_per_segment_results() -> None:
    partial_gateway = PartialFailVideoGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=partial_gateway,
        )
        provider_id = _create_provider(client, headers)

        response = client.post(
            "/api/v1/generations/videos/batch",
            json={
                "provider_id": provider_id,
                "model": "forge-video-v1",
                "prompt": "赛博城市追逐短片",
                "segments": [
                    {
                        "segment_index": 1,
                        "title": "开场钩子",
                        "duration_seconds": 10,
                        "visual_prompt": "夜色城市俯拍，霓虹闪烁",
                        "narration_text": "雨夜里，主角独自穿过空旷街头。",
                    },
                    {
                        "segment_index": 2,
                        "title": "冲突升级",
                        "duration_seconds": 10,
                        "visual_prompt": "镜头快速推进，敌人逼近",
                        "narration_text": "警报骤然响起，身后的追兵越来越近。",
                    },
                ],
                "options": {"resolution": "720p"},
            },
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["segment_count"] == 2
    assert body["segments"][0]["status"] == "success"
    assert body["segments"][0]["generation"]["outputs"][0]["duration_seconds"] == 10
    assert body["segments"][1]["status"] == "error"
    assert "second segment failed" in body["segments"][1]["error_detail"]


def test_generate_multi_video_isolates_segment_prompts_and_enables_audio_by_default() -> None:
    recording_gateway = RecordingVideoGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=recording_gateway,
        )
        provider_id = _create_provider(client, headers, adapter_type="volcengine_ark")

        response = client.post(
            "/api/v1/generations/videos/batch",
            json={
                "provider_id": provider_id,
                "model": "forge-video-v1",
                "prompt": "凡人修仙开场，突出仙宗震撼感",
                "segments": [
                    {
                        "segment_index": 1,
                        "title": "云海仙宗",
                        "duration_seconds": 10,
                        "visual_prompt": "远景航拍，浩瀚云海翻涌，七座主峰刺破苍穹",
                        "narration_text": "云海翻涌，七座主峰如巨剑刺破苍穹。",
                    },
                    {
                        "segment_index": 2,
                        "title": "初见震撼",
                        "duration_seconds": 10,
                        "visual_prompt": "中景推近韩立侧脸，瞳孔中倒映霞光与楼阁",
                        "narration_text": "这就是修仙大派？落云宗立派三千年。",
                    },
                    {
                        "segment_index": 3,
                        "title": "拜别入宗",
                        "duration_seconds": 10,
                        "visual_prompt": "师徒二人沿青石长阶上山，身影没入云雾",
                        "narration_text": "弟子定当勤勉。外门弟子三千，内门八百。",
                    },
                ],
            },
            headers=headers,
        )

    assert response.status_code == 200
    assert len(recording_gateway.video_payloads) == 3

    prompts = [item["payload"].resolved_prompt or "" for item in recording_gateway.video_payloads]
    assert all("只允许使用当前分段信息" in prompt for prompt in prompts)
    assert "云海翻涌，七座主峰如巨剑刺破苍穹。" in prompts[0]
    assert "这就是修仙大派？落云宗立派三千年。" not in prompts[0]
    assert "弟子定当勤勉。外门弟子三千，内门八百。" not in prompts[0]
    assert "这就是修仙大派？落云宗立派三千年。" in prompts[1]
    assert "弟子定当勤勉。外门弟子三千，内门八百。" not in prompts[1]
    assert "弟子定当勤勉。外门弟子三千，内门八百。" in prompts[2]

    options = [item["payload"].options for item in recording_gateway.video_payloads]
    assert all(item["generate_audio"] is True for item in options)


def test_generate_multi_video_preserves_explicit_generate_audio_false() -> None:
    recording_gateway = RecordingVideoGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=recording_gateway,
        )
        provider_id = _create_provider(client, headers, adapter_type="volcengine_ark")

        response = client.post(
            "/api/v1/generations/videos/batch",
            json={
                "provider_id": provider_id,
                "model": "forge-video-v1",
                "prompt": "赛博都市追逐短片",
                "segments": [
                    {
                        "segment_index": 1,
                        "title": "开场",
                        "duration_seconds": 10,
                        "visual_prompt": "雨夜霓虹街头，主角奔跑",
                        "narration_text": "警报声拉响，脚步声逼近。",
                    }
                ],
                "options": {"generate_audio": False},
            },
            headers=headers,
        )

    assert response.status_code == 200
    assert len(recording_gateway.video_payloads) == 1
    assert recording_gateway.video_payloads[0]["payload"].options["generate_audio"] is False


def test_generate_video_enables_audio_by_default_for_volcengine_ark() -> None:
    fake_gateway = FakeProviderGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=fake_gateway,
        )
        provider_id = _create_provider(client, headers, adapter_type="volcengine_ark")

        response = client.post(
            "/api/v1/generations/videos",
            json={
                "provider_id": provider_id,
                "model": "forge-video-v1",
                "count": 1,
                "prompt": "雨夜街头追逐镜头",
            },
            headers=headers,
        )

    assert response.status_code == 200
    assert fake_gateway.last_video_payload is not None
    assert fake_gateway.last_video_payload["payload"].options["generate_audio"] is True


def test_regenerate_multi_video_segment_returns_single_result() -> None:
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
            "/api/v1/generations/videos/segments/regenerate",
            json={
                "provider_id": provider_id,
                "model": "forge-video-v1",
                "prompt": "赛博城市镜头",
                "segment": {
                    "segment_index": 1,
                    "title": "重制片段",
                    "duration_seconds": 8,
                    "visual_prompt": "雨中巷弄的高速跟随镜头",
                    "narration_text": "他在霓虹的反射中急速奔跑，心跳加速。",
                },
                "scene_prompt_texts": ["城市追逐，节奏紧张"],
            },
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["visual_prompt"] == "雨中巷弄的高速跟随镜头"
    assert body["generation"]["outputs"][0]["url"] == "https://cdn.example.com/generated/video-1.mp4"
    assert body["token_usage"]["total_tokens"] == 165


def test_regenerate_multi_video_segment_propagates_errors() -> None:
    partial_gateway = PartialFailVideoGateway()

    with TestClient(app) as client:
        headers = register_and_get_headers(client)
        app.state.generation_service = GenerationService(
            provider_service=app.state.provider_service,
            asset_service=app.state.asset_service,
            provider_gateway=partial_gateway,
        )
        provider_id = _create_provider(client, headers)

        response = client.post(
            "/api/v1/generations/videos/segments/regenerate",
            json={
                "provider_id": provider_id,
                "model": "forge-video-v1",
                "prompt": "赛博城市镜头",
                "segment": {
                    "segment_index": 2,
                    "title": "冲突升级",
                    "duration_seconds": 10,
                    "visual_prompt": "镜头快速推进，敌人逼近",
                    "narration_text": "警报骤然响起，身后的追兵越来越近。",
                },
            },
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert "second segment failed" in body["error_detail"]


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
