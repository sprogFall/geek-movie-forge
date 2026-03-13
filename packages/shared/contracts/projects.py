from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from packages.shared.enums.project_status import ProjectStatus


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    aspect_ratio: str = Field(min_length=1)
    status: ProjectStatus = ProjectStatus.ACTIVE


class ProjectResponse(BaseModel):
    project_id: str
    title: str
    summary: str
    platform: str
    aspect_ratio: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]


class ProjectRecord(BaseModel):
    project_id: str
    owner_id: str
    title: str
    summary: str
    platform: str
    aspect_ratio: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    def to_response(self) -> ProjectResponse:
        return ProjectResponse(
            project_id=self.project_id,
            title=self.title,
            summary=self.summary,
            platform=self.platform,
            aspect_ratio=self.aspect_ratio,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

