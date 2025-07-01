from fastapi import APIRouter

from src.api.routes import users, utils
from src.auth import router as auth_router
from src.canvas.router import router as canvas_router
from src.question.router import router as question_router
from src.quiz.router import router as quiz_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(canvas_router)
api_router.include_router(quiz_router)
api_router.include_router(question_router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
