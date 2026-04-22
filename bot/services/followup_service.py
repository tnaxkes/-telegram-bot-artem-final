from datetime import datetime, timezone

from telegram.ext import Application

from bot.content.loader import get_funnel_config
from bot.models.db import User
from bot.models.enums import TaskType
from bot.services.scheduler_service import SchedulerService


class FollowupService:
    def __init__(self, scheduler_service: SchedulerService):
        self.scheduler_service = scheduler_service
        self.funnel = get_funnel_config()

    async def schedule_lesson_followups(self, application: Application, user: User, lesson_code: str) -> None:
        step = self.funnel.steps[lesson_code]
        schedule_batch = int(datetime.now(timezone.utc).timestamp())
        for item in step.followups:
            payload = {'message_code': item.code, 'lesson_code': lesson_code}
            if lesson_code == 'lesson_1':
                payload['next_step'] = 'lesson_2'
            elif lesson_code == 'lesson_2':
                payload['next_step'] = 'lesson_3'
            elif lesson_code == 'lesson_3':
                payload = {'message_code': None, 'next_step': 'application_offer'}
            dedup_key = f'user:{user.id}:task:{item.code}:batch:{schedule_batch}'
            await self.scheduler_service.schedule_task(
                application=application,
                user=user,
                task_type=TaskType.LESSON_FOLLOWUP,
                dedup_key=dedup_key,
                run_at=self.scheduler_service.run_at_after(item.delay_seconds),
                payload=payload,
            )

    async def schedule_next_lesson_nudges(self, application: Application, user: User, lesson_number: int) -> None:
        schedule_batch = int(datetime.now(timezone.utc).timestamp())
        if lesson_number == 2:
            codes = ['lesson_2_nudge_1', 'lesson_2_nudge_2', 'lesson_2_nudge_3']
        elif lesson_number == 3:
            codes = ['lesson_3_nudge_1', 'lesson_3_nudge_2', 'lesson_3_nudge_3']
        else:
            return

        for index, code in enumerate(codes, start=1):
            dedup_key = f'user:{user.id}:task:{code}:batch:{schedule_batch}'
            await self.scheduler_service.schedule_task(
                application=application,
                user=user,
                task_type=TaskType.LESSON_FOLLOWUP,
                dedup_key=dedup_key,
                run_at=self.scheduler_service.run_at_after(20 * index),
                payload={
                    'message_code': code,
                    'next_step': f'lesson_{lesson_number}',
                    'nudge_for': lesson_number,
                },
            )

    async def schedule_application_followups(self, application: Application, user: User) -> None:
        schedule_batch = int(datetime.now(timezone.utc).timestamp())
        for item in self.funnel.application_followups:
            dedup_key = f'user:{user.id}:task:{item.code}:batch:{schedule_batch}'
            await self.scheduler_service.schedule_task(
                application=application,
                user=user,
                task_type=TaskType.APPLICATION_FOLLOWUP,
                dedup_key=dedup_key,
                run_at=self.scheduler_service.run_at_after(item.delay_seconds),
                payload={'message_code': item.code, 'application': True},
            )
