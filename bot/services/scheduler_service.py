from __future__ import annotations

from datetime import datetime, timedelta, timezone

from telegram.ext import Application

from bot.models.db import ScheduledTask, User
from bot.models.enums import EventType, TaskStatus, TaskType
from bot.repositories.event_repository import EventRepository
from bot.repositories.task_repository import TaskRepository


class SchedulerService:
    def __init__(self, task_repository: TaskRepository, event_repository: EventRepository):
        self.task_repository = task_repository
        self.event_repository = event_repository

    async def schedule_task(
        self,
        *,
        application: Application,
        user: User,
        task_type: TaskType,
        dedup_key: str,
        run_at: datetime,
        payload: dict,
    ) -> tuple[ScheduledTask, bool]:
        task, created = await self.task_repository.create_if_not_exists(
            user_id=user.id,
            task_type=task_type.value,
            dedup_key=dedup_key,
            run_at=run_at,
            payload=payload,
        )
        if not created:
            return task, False

        application.job_queue.run_once(
            callback=application.bot_data['scheduled_task_callback'],
            when=run_at,
            name=dedup_key,
            data={'task_id': task.id},
        )
        await self.task_repository.update_enqueued(task, redis_job_id=dedup_key)
        await self.event_repository.create(
            user_id=user.id,
            event_type=EventType.MANUAL_ACTION.value,
            stage=user.current_stage,
            payload={'task_type': task_type.value, 'dedup_key': dedup_key, 'run_at': run_at.isoformat()},
        )
        return task, True

    async def cancel_tasks_for_user(self, user_id: int, task_type: TaskType | None = None) -> int:
        cancelled = await self.task_repository.cancel_for_user(user_id, task_type.value if task_type else None)
        if cancelled:
            await self.event_repository.create(
                user_id=user_id,
                event_type=EventType.TASK_CANCELLED.value,
                payload={'task_type': task_type.value if task_type else None, 'count': cancelled},
            )
        return cancelled

    async def recover_pending_tasks(self, application: Application) -> int:
        tasks = await self.task_repository.list_pending()
        count = 0
        now = datetime.now(timezone.utc)
        for task in tasks:
            if task.status == TaskStatus.CANCELLED.value:
                continue
            run_at = task.run_at
            if run_at.tzinfo is None:
                run_at = run_at.replace(tzinfo=timezone.utc)
            when = run_at if run_at > now else now + timedelta(seconds=1)
            application.job_queue.run_once(
                callback=application.bot_data['scheduled_task_callback'],
                when=when,
                name=task.dedup_key,
                data={'task_id': task.id},
            )
            count += 1
        return count

    @staticmethod
    def run_at_after(seconds: int) -> datetime:
        return datetime.now(timezone.utc) + timedelta(seconds=seconds)
