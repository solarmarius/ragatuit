from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    canvas_user_id: str
    access_token: str
    refresh_token: str
