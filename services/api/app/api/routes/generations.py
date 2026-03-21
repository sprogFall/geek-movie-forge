from fastapi import APIRouter, Depends, status

from packages.shared.contracts.auth import UserResponse
from services.api.app.dependencies.auth import get_current_user
from services.api.app.dependencies.services import (
    get_generation_service,
    get_video_generation_task_service,
)
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
    VideoGenerationTaskListResponse,
    VideoGenerationTaskResponse,
    VideoGenerationRequest,
)
from services.api.app.services.generation_service import GenerationService
from services.api.app.services.video_generation_task_service import (
    InMemoryVideoGenerationTaskService,
)

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


@router.post(
    "/videos/async",
    response_model=VideoGenerationTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_video_async(
    payload: VideoGenerationRequest,
    current_user: UserResponse = Depends(get_current_user),
    video_generation_task_service: InMemoryVideoGenerationTaskService = Depends(
        get_video_generation_task_service
    ),
) -> VideoGenerationTaskResponse:
    return await video_generation_task_service.submit_single_video(current_user.user_id, payload)


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


@router.post(
    "/videos/batch/async",
    response_model=VideoGenerationTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_multi_video_async(
    payload: MultiVideoGenerationRequest,
    current_user: UserResponse = Depends(get_current_user),
    video_generation_task_service: InMemoryVideoGenerationTaskService = Depends(
        get_video_generation_task_service
    ),
) -> VideoGenerationTaskResponse:
    return await video_generation_task_service.submit_multi_video(current_user.user_id, payload)


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


@router.get("/video-tasks", response_model=VideoGenerationTaskListResponse)
async def list_video_generation_tasks(
    current_user: UserResponse = Depends(get_current_user),
    video_generation_task_service: InMemoryVideoGenerationTaskService = Depends(
        get_video_generation_task_service
    ),
) -> VideoGenerationTaskListResponse:
    return await video_generation_task_service.list_tasks(current_user.user_id)


@router.get("/video-tasks/{task_id}", response_model=VideoGenerationTaskResponse)
async def get_video_generation_task(
    task_id: str,
    current_user: UserResponse = Depends(get_current_user),
    video_generation_task_service: InMemoryVideoGenerationTaskService = Depends(
        get_video_generation_task_service
    ),
) -> VideoGenerationTaskResponse:
    return await video_generation_task_service.get_task(current_user.user_id, task_id)


@router.post("/texts", response_model=TextGenerationResponse)
async def generate_text(
    payload: TextGenerationRequest,
    current_user: UserResponse = Depends(get_current_user),
    generation_service: GenerationService = Depends(get_generation_service),
) -> TextGenerationResponse:
    return await generation_service.generate_text(current_user.user_id, payload)
