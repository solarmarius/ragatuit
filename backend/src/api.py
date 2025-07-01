"""
Main API router setup and utility endpoints.
"""

from fastapi import APIRouter

from src.auth import router as auth_router
from src.auth import users_router
from src.canvas.router import router as canvas_router
from src.question.router import router as question_router
from src.quiz.router import router as quiz_router

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
