from fastapi import APIRouter, Depends

from packages.shared.contracts.auth import UserResponse
from services.api.app.dependencies.auth import get_current_user
from services.api.app.dependencies.services import get_generation_service
from services.api.app.schemas.generations import (
    ImageGenerationRequest,
    MediaGenerationResponse,
    MultiVideoGenerationRequest,
    MultiVideoGenerationResponse,
    MultiVideoPlanRequest,
    MultiVideoPlanResponse,
    MultiVideoSegmentGenerationResult,
    MultiVideoSegmentRegenerationRequest,
    TextGenerationRequest,
    TextGenerationResponse,
    VideoGenerationRequest,
)
from services.api.app.services.generation_service import GenerationService

router = APIRouter(prefix="/api/v1/generations", tags=["generations"])


@router.post("/images", response_model=MediaGenerationResponse)
async def generate_image(
    payload: ImageGenerationRequest,
    current_user: UserResponse = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> MediaGenerationResponse:
    return await generation_service.generate_image(current_user.user_id, payload)


@router.post("/videos", response_model=MediaGenerationResponse)
async def generate_video(
    payload: VideoGenerationRequest,
    current_user: UserResponse = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> MediaGenerationResponse:
    return await generation_service.generate_video(current_user.user_id, payload)


@router.post("/videos/plan", response_model=MultiVideoPlanResponse)
async def plan_multi_video(
    payload: MultiVideoPlanRequest,
    current_user: UserResponse = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> MultiVideoPlanResponse:
    return await generation_service.plan_multi_video(current_user.user_id, payload)


@router.post("/videos/batch", response_model=MultiVideoGenerationResponse)
async def generate_multi_video(
    payload: MultiVideoGenerationRequest,
    current_user: UserResponse = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> MultiVideoGenerationResponse:
    return await generation_service.generate_multi_video(current_user.user_id, payload)


@router.post("/videos/segments/regenerate", response_model=MultiVideoSegmentGenerationResult)
async def regenerate_multi_video_segment(
    payload: MultiVideoSegmentRegenerationRequest,
    current_user: UserResponse = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> MultiVideoSegmentGenerationResult:
    return await generation_service.regenerate_multi_video_segment(
        current_user.user_id,
        payload,
    )


@router.post("/texts", response_model=TextGenerationResponse)
async def generate_text(
    payload: TextGenerationRequest,
    current_user: UserResponse = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> TextGenerationResponse:
    return await generation_service.generate_text(current_user.user_id, payload)
