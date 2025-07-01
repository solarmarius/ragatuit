from typing import Any

from fastapi import APIRouter

from src.database import check_database_health
from src.logging_config import get_logger

router = APIRouter(prefix="/utils", tags=["utils"])
logger = get_logger("utils")


@router.get("/health-check/")
async def health_check() -> bool:
    return True


@router.get("/health/db")
async def get_db_health() -> dict[str, Any]:
    """
    Check database connection pool health.
    """
    logger.info("database_health_check_requested")
    health_status = check_database_health()
    logger.info("database_health_check_completed", status=health_status["status"])
    return health_status
