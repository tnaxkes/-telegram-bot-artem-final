from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.db import UserEvent


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, event_type: str, stage: str | None = None, payload: dict | None = None) -> UserEvent:
        event = UserEvent(user_id=user_id, event_type=event_type, stage=stage, payload=payload or {})
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_for_user(self, user_id: int) -> list[UserEvent]:
        result = await self.session.execute(
            select(UserEvent).where(UserEvent.user_id == user_id).order_by(UserEvent.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_recent(self, limit: int = 20) -> list[UserEvent]:
        result = await self.session.execute(
            select(UserEvent).order_by(UserEvent.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
