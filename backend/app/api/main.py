from fastapi import APIRouter

from app.api.routes import canvas, questions, quiz, users, utils
from app.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(canvas.router)
api_router.include_router(quiz.router)
api_router.include_router(questions.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
