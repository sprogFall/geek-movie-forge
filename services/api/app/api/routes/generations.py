from fastapi import APIRouter, Depends

from packages.shared.contracts.auth import UserResponse
from services.api.app.dependencies.auth import get_current_user
from services.api.app.dependencies.services import get_generation_service
from services.api.app.schemas.generations import (
    ImageGenerationRequest,
    MediaGenerationResponse,
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


@router.post("/texts", response_model=TextGenerationResponse)
async def generate_text(
    payload: TextGenerationRequest,
    current_user: UserResponse = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> TextGenerationResponse:
    return await generation_service.generate_text(current_user.user_id, payload)
