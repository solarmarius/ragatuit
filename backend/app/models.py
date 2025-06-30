from typing import TYPE_CHECKING

from sqlmodel import SQLModel

if TYPE_CHECKING:
    pass


# User models moved to app.auth.models and app.auth.schemas


# Quiz model and schemas moved to app.quiz.models and app.quiz.schemas


# Auth schemas moved to app.auth.schemas


# Generic message
class Message(SQLModel):
    message: str


# Canvas auth schemas moved to app.auth.schemas


class CanvasConfigResponse(SQLModel):
    authorization_url: str
    client_id: str
    redirect_uri: str
    scope: str


# Question model and schemas moved to app.question.models and app.question.schemas
