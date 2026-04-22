import logging

from telegram.ext import CallbackContext

from bot.repositories.event_repository import EventRepository
from bot.repositories.task_repository import TaskRepository
from bot.repositories.user_repository import UserRepository
from bot.services.funnel_service import FunnelService
from config.database import AsyncSessionLocal


logger = logging.getLogger(__name__)


async def run_scheduled_task(context: CallbackContext) -> None:
    task_id = context.job.data['task_id']

    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        funnel_service = FunnelService(context.bot, user_repository, event_repository, task_repository)

        task = await task_repository.get(task_id)
        if task is None:
            logger.warning('Scheduled task %s not found', task_id)
            return
        user = await user_repository.get_by_id(task.user_id)
        if user is None or user.unsubscribed:
            return
        if task.status in {'cancelled', 'sent'}:
            return
        if user.application_submitted and task.task_type == 'application_followup':
            await task_repository.cancel_for_user(user.id, task.task_type)
            await session.commit()
            return

        await task_repository.mark_processing(task)
        try:
            payload = task.payload or {}
            message_code = payload.get('message_code')
            next_step = payload.get('next_step')
            if message_code:
                await funnel_service.send_followup_message(user, message_code, next_step=next_step, application=context.application)
            if next_step == 'application_offer':
                await funnel_service.send_offer(user, context.application)
            await task_repository.mark_sent(task)
        except Exception as exc:
            logger.exception('Failed to process scheduled task %s', task_id)
            await task_repository.mark_failed(task, str(exc))
        finally:
            await session.commit()
