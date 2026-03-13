from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from packages.shared.enums.task_status import TaskStatus


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    project_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    platform: str = Field(min_length=1)


class TaskResponse(BaseModel):
    task_id: str
    project_id: str
    title: str
    source_text: str
    platform: str
    status: TaskStatus
    created_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
