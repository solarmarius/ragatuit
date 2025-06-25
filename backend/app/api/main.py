from fastapi import APIRouter

from app.api.routes import auth, canvas, questions, quiz, users, utils

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(canvas.router)
api_router.include_router(questions.router)
api_router.include_router(quiz.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
