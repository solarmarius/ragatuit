import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.core.middleware.logging_middleware import LoggingMiddleware


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


# Configure logging first
configure_logging()
logger = get_logger("main")

if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)
    logger.info("sentry_initialized", dsn=str(settings.SENTRY_DSN))

app = FastAPI(
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

app.include_router(api_router, prefix=settings.API_V1_STR)
logger.info("api_router_included", prefix=settings.API_V1_STR)
