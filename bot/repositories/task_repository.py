from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.db import ScheduledTask
from bot.models.enums import TaskStatus


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_dedup_key(self, dedup_key: str) -> ScheduledTask | None:
        result = await self.session.execute(select(ScheduledTask).where(ScheduledTask.dedup_key == dedup_key))
        return result.scalar_one_or_none()

    async def create_if_not_exists(
        self,
        *,
        user_id: int,
        task_type: str,
        dedup_key: str,
        run_at: datetime,
        payload: dict,
    ) -> tuple[ScheduledTask, bool]:
        existing = await self.get_by_dedup_key(dedup_key)
        if existing:
            return existing, False

        task = ScheduledTask(
            user_id=user_id,
            task_type=task_type,
            dedup_key=dedup_key,
            run_at=run_at,
            payload=payload,
            status=TaskStatus.PENDING.value,
        )
        self.session.add(task)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            existing = await self.get_by_dedup_key(dedup_key)
            if existing is None:
                raise
            return existing, False
        return task, True

    async def update_enqueued(self, task: ScheduledTask, redis_job_id: str) -> ScheduledTask:
        task.status = TaskStatus.ENQUEUED.value
        task.redis_job_id = redis_job_id
        await self.session.flush()
        return task

    async def mark_processing(self, task: ScheduledTask) -> ScheduledTask:
        task.status = TaskStatus.PROCESSING.value
        await self.session.flush()
        return task

    async def mark_sent(self, task: ScheduledTask) -> ScheduledTask:
        task.status = TaskStatus.SENT.value
        task.sent_at = datetime.now(timezone.utc)
        await self.session.flush()
        return task

    async def mark_failed(self, task: ScheduledTask, error_message: str) -> ScheduledTask:
        task.status = TaskStatus.FAILED.value
        task.error_message = error_message
        task.retries += 1
        await self.session.flush()
        return task

    async def cancel_for_user(self, user_id: int, task_type: str | None = None) -> int:
        query = select(ScheduledTask).where(
            ScheduledTask.user_id == user_id,
            ScheduledTask.status.in_([
                TaskStatus.PENDING.value,
                TaskStatus.ENQUEUED.value,
                TaskStatus.PROCESSING.value,
            ]),
        )
        if task_type:
            query = query.where(ScheduledTask.task_type == task_type)
        result = await self.session.execute(query)
        tasks = list(result.scalars().all())
        now = datetime.now(timezone.utc)
        for task in tasks:
            task.status = TaskStatus.CANCELLED.value
            task.cancelled_at = now
        await self.session.flush()
        return len(tasks)

    async def list_pending(self) -> list[ScheduledTask]:
        result = await self.session.execute(
            select(ScheduledTask).where(
                ScheduledTask.status.in_([TaskStatus.PENDING.value, TaskStatus.ENQUEUED.value])
            )
        )
        return list(result.scalars().all())

    async def list_for_user(self, user_id: int) -> list[ScheduledTask]:
        result = await self.session.execute(
            select(ScheduledTask).where(ScheduledTask.user_id == user_id).order_by(ScheduledTask.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, task_id: int) -> ScheduledTask | None:
        result = await self.session.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))
        return result.scalar_one_or_none()
