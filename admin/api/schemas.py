from datetime import datetime

from pydantic import BaseModel, Field


class MoveStageRequest(BaseModel):
    stage: str
    send_message: bool = True


class ManualMessageRequest(BaseModel):
    text: str | None = None
    message_code: str | None = None
    with_application_button: bool = False


class ApplicationCompleteRequest(BaseModel):
    user_id: int | None = None
    telegram_id: int | None = None
    note: str | None = None


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    status: str
    current_stage: str
    current_lesson: int
    source: str | None
    application_opened: bool
    application_submitted: bool
    unsubscribed: bool
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, user):
        return cls(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            first_name=user.first_name,
            status=user.status,
            current_stage=user.current_stage,
            current_lesson=user.current_lesson,
            source=user.source,
            application_opened=user.application_opened,
            application_submitted=user.application_submitted,
            unsubscribed=user.unsubscribed,
            tags=user.tags or [],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
