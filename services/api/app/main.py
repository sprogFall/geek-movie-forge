import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from packages.provider_sdk.gateway import HttpProviderGateway
from services.api.app.api.routes.assets import router as assets_router
from services.api.app.api.routes.auth import router as auth_router
from services.api.app.api.routes.call_logs import router as call_logs_router
from services.api.app.api.routes.generations import router as generations_router
from services.api.app.api.routes.health import router as health_router
from services.api.app.api.routes.projects import router as projects_router
from services.api.app.api.routes.providers import router as providers_router
from services.api.app.api.routes.tasks import router as tasks_router
from services.api.app.core.config import get_settings
from services.api.app.core.store import JsonFileStore
from services.api.app.services.asset_service import InMemoryAssetService
from services.api.app.services.auth_service import InMemoryAuthService
from services.api.app.services.call_log_service import InMemoryCallLogService
from services.api.app.services.errors import ServiceError
from services.api.app.services.generation_service import GenerationService
from services.api.app.services.project_service import InMemoryProjectService
from services.api.app.services.provider_service import InMemoryProviderService
from services.api.app.services.task_service import InMemoryTaskService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    store: JsonFileStore | None = None
    if settings.persist_enabled:
        store = JsonFileStore(Path(settings.persist_dir))

    app.state.auth_service = InMemoryAuthService(
        jwt_secret=settings.jwt_secret,
        jwt_expire_minutes=settings.jwt_expire_minutes,
        store=store,
    )
    app.state.project_service = InMemoryProjectService(store=store)
    app.state.task_service = InMemoryTaskService(store=store)
    app.state.provider_service = InMemoryProviderService(store=store)
    app.state.asset_service = InMemoryAssetService(store=store)
    app.state.provider_gateway = HttpProviderGateway()
    app.state.call_log_service = InMemoryCallLogService(store=store)
    app.state.generation_service = GenerationService(
        provider_service=app.state.provider_service,
        asset_service=app.state.asset_service,
        provider_gateway=app.state.provider_gateway,
        call_log_service=app.state.call_log_service,
    )
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ServiceError)
async def handle_service_error(request: Request, exc: ServiceError) -> JSONResponse:
    logger.warning(
        "ServiceError: method=%s path=%s status=%s detail=%s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.detail,
        exc_info=exc.status_code >= 500,
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(providers_router)
app.include_router(assets_router)
app.include_router(generations_router)
app.include_router(call_logs_router)
