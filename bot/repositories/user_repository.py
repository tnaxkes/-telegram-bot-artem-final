from datetime import datetime, timezone

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.db import User
from bot.models.enums import UserStatus


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list_users(
        self,
        status: str | None = None,
        source: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> list[User]:
        query: Select[tuple[User]] = select(User).order_by(User.created_at.desc())
        if status:
            query = query.where(User.status == status)
        if source:
            query = query.where(User.source == source)
        if created_from:
            query = query.where(User.created_at >= created_from)
        if created_to:
            query = query.where(User.created_at <= created_to)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_or_update_from_telegram(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        source: str | None,
    ) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        created = False
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                source=source,
                status=UserStatus.NEW.value,
                current_stage='start',
                last_interaction_at=datetime.now(timezone.utc),
            )
            self.session.add(user)
            created = True
        else:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.source = user.source or source
            user.last_interaction_at = datetime.now(timezone.utc)
        await self.session.flush()
        return user, created

    async def update_status(self, user: User, status: UserStatus, stage: str | None = None) -> User:
        user.status = status.value
        if stage:
            user.current_stage = stage
        user.last_interaction_at = datetime.now(timezone.utc)
        await self.session.flush()
        return user

    async def mark_application_opened(self, user: User) -> User:
        user.application_opened = True
        user.status = UserStatus.APPLICATION_OPENED.value
        user.current_stage = 'application_offer'
        user.last_interaction_at = datetime.now(timezone.utc)
        await self.session.flush()
        return user

    async def mark_application_submitted(self, user: User) -> User:
        user.application_submitted = True
        user.status = UserStatus.APPLICATION_SUBMITTED.value
        user.current_stage = 'application_submitted'
        user.last_interaction_at = datetime.now(timezone.utc)
        await self.session.flush()
        return user

    async def set_stage(self, user: User, stage: str, lesson: int | None = None) -> User:
        user.current_stage = stage
        if lesson is not None:
            user.current_lesson = lesson
            user.lesson_2_reached = user.lesson_2_reached or lesson >= 2
            user.lesson_3_reached = user.lesson_3_reached or lesson >= 3
        user.last_interaction_at = datetime.now(timezone.utc)
        await self.session.flush()
        return user

    async def stop_user(self, user: User) -> User:
        user.unsubscribed = True
        user.status = UserStatus.LOST.value
        user.last_interaction_at = datetime.now(timezone.utc)
        await self.session.flush()
        return user
