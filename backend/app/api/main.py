from fastapi import APIRouter

from app.api.routes import questions, users, utils
from app.auth import router as auth_router
from app.canvas.router import router as canvas_router
from app.quiz.router import router as quiz_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(canvas_router)
api_router.include_router(quiz_router)
api_router.include_router(questions.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
