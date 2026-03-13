from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.api.app.api.routes.health import router as health_router
from services.api.app.api.routes.tasks import router as tasks_router
from services.api.app.core.config import get_settings
from services.api.app.services.task_service import InMemoryTaskService


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.task_service = InMemoryTaskService()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health_router)
app.include_router(tasks_router)
