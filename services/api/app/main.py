import logging
from contextlib import asynccontextmanager

from packages.db.session import create_database_engine, create_session_factory, initialize_database
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
from services.api.app.middleware.api_logging import ApiLoggingMiddleware
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
    engine = create_database_engine(
        db_backend=settings.db_backend,
        database_url=settings.database_url,
    )
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    app.state.db_engine = engine

    app.state.auth_service = InMemoryAuthService(
        jwt_secret=settings.jwt_secret,
        jwt_expire_minutes=settings.jwt_expire_minutes,
        session_factory=session_factory,
    )
    app.state.project_service = InMemoryProjectService(session_factory=session_factory)
    app.state.task_service = InMemoryTaskService(session_factory=session_factory)
    app.state.provider_service = InMemoryProviderService(session_factory=session_factory)
    app.state.asset_service = InMemoryAssetService(session_factory=session_factory)
    app.state.provider_gateway = HttpProviderGateway()
    app.state.call_log_service = InMemoryCallLogService(session_factory=session_factory)
    app.state.generation_service = GenerationService(
        provider_service=app.state.provider_service,
        asset_service=app.state.asset_service,
        provider_gateway=app.state.provider_gateway,
        call_log_service=app.state.call_log_service,
    )
    yield
    engine.dispose()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    ApiLoggingMiddleware,
    skip_paths={"/healthz"},
    max_request_size_bytes=settings.api_max_request_bytes,
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
