from fastapi import Request

from services.api.app.services.task_service import InMemoryTaskService


def get_task_service(request: Request) -> InMemoryTaskService:
    return request.app.state.task_service
