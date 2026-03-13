"""Shared contracts."""

from packages.shared.contracts.assets import AssetCreateRequest, AssetListResponse, AssetResponse
from packages.shared.contracts.generations import (
    ImageGenerationRequest,
    MediaGenerationResponse,
    ProviderMediaGenerationResult,
    ProviderTextGenerationResult,
    TextGenerationRequest,
    TextGenerationResponse,
    VideoGenerationRequest,
)
from packages.shared.contracts.providers import (
    ProviderConfigCreateRequest,
    ProviderConfigUpdateRequest,
    ProviderListResponse,
    ProviderResponse,
)
from packages.shared.contracts.tasks import TaskCreateRequest, TaskResponse

__all__ = [
    "AssetCreateRequest",
    "AssetListResponse",
    "AssetResponse",
    "ImageGenerationRequest",
    "MediaGenerationResponse",
    "ProviderConfigCreateRequest",
    "ProviderConfigUpdateRequest",
    "ProviderListResponse",
    "ProviderMediaGenerationResult",
    "ProviderResponse",
    "ProviderTextGenerationResult",
    "TaskCreateRequest",
    "TaskResponse",
    "TextGenerationRequest",
    "TextGenerationResponse",
    "VideoGenerationRequest",
]
