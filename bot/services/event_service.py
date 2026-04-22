from bot.models.enums import EventType
from bot.repositories.event_repository import EventRepository


class EventService:
    def __init__(self, event_repository: EventRepository):
        self.event_repository = event_repository

    async def log(self, user_id: int, event_type: EventType, stage: str | None = None, payload: dict | None = None) -> None:
        await self.event_repository.create(user_id=user_id, event_type=event_type.value, stage=stage, payload=payload or {})
