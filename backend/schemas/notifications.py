from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models import LogStatus


class NotificationCreate(BaseModel):
    category_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=1_000)


class NotificationAccepted(BaseModel):
    accepted: bool
    category_id: int
    message: str


class NotificationLogRead(BaseModel):
    id: UUID
    message: str
    category_id: int | None
    category_name: str | None
    channel_id: int | None
    channel_name: str | None
    user_id: UUID | None
    user_name: str | None
    status: LogStatus
    error_message: str | None
    created_at: datetime


class NotificationLogModel(BaseModel):
    id: UUID
    message: str
    category_id: int | None
    channel_id: int | None
    user_id: UUID | None
    status: LogStatus
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
