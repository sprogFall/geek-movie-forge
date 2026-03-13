from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from packages.provider_sdk.gateway import HttpProviderGateway
from services.api.app.api.routes.assets import router as assets_router
from services.api.app.api.routes.generations import router as generations_router
from services.api.app.api.routes.health import router as health_router
from services.api.app.api.routes.providers import router as providers_router
from services.api.app.api.routes.tasks import router as tasks_router
from services.api.app.core.config import get_settings
from services.api.app.services.asset_service import InMemoryAssetService
from services.api.app.services.errors import ServiceError
from services.api.app.services.generation_service import GenerationService
from services.api.app.services.provider_service import InMemoryProviderService
from services.api.app.services.task_service import InMemoryTaskService


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.task_service = InMemoryTaskService()
    app.state.provider_service = InMemoryProviderService()
    app.state.asset_service = InMemoryAssetService()
    app.state.provider_gateway = HttpProviderGateway()
    app.state.generation_service = GenerationService(
        provider_service=app.state.provider_service,
        asset_service=app.state.asset_service,
        provider_gateway=app.state.provider_gateway,
    )
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.exception_handler(ServiceError)
async def handle_service_error(_, exc: ServiceError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(providers_router)
app.include_router(assets_router)
app.include_router(generations_router)
