import sentry_sdk
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

# Import all models to ensure SQLAlchemy can resolve relationships
import src.auth.models  # noqa
import src.question.models  # noqa
import src.quiz.models  # noqa
from src.auth import router as auth_router
from src.auth import users_router
from src.canvas.router import router as canvas_router
from src.config import configure_logging, get_logger, settings
from src.exceptions import (
    ServiceError,
    general_exception_handler,
    service_error_handler,
)
from src.middleware import LoggingMiddleware
from src.question.router import router as question_router
from src.quiz.router import router as quiz_router


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


# Configure logging first
configure_logging()
logger = get_logger("main")

if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)
    logger.info("sentry_initialized", dsn=str(settings.SENTRY_DSN))

app: FastAPI = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

logger.info(
    "fastapi_app_created",
    project_name=settings.PROJECT_NAME,
    environment=settings.ENVIRONMENT,
)

# Add logging middleware first
app.add_middleware(LoggingMiddleware)
logger.info("logging_middleware_added")

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("cors_middleware_added", origins=settings.all_cors_origins)


# Create main API router
api_router = APIRouter()

# Include all module routers
api_router.include_router(auth_router)
api_router.include_router(
    users_router
)  # User management endpoints without /auth prefix
api_router.include_router(canvas_router)
api_router.include_router(quiz_router)
api_router.include_router(question_router)


# Health check endpoint (moved from api/routes/utils.py)
@api_router.get("/utils/health-check/", tags=["utils"])
async def health_check() -> bool:
    """
    Simple health check endpoint.

    Returns True if the API is running and responsive.
    Used for monitoring and load balancer health checks.
    """
    return True


# Add global exception handlers
@app.exception_handler(ServiceError)
async def handle_service_error(request: Request, exc: ServiceError) -> JSONResponse:
    return await service_error_handler(request, exc)


@app.exception_handler(Exception)
async def handle_general_error(request: Request, exc: Exception) -> JSONResponse:
    return await general_exception_handler(request, exc)


logger.info("global_exception_handlers_added")

app.include_router(api_router)
logger.info("api_router_included", prefix=settings.API_V1_STR)
