import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.models.enums import EventType, TaskType
from bot.repositories.event_repository import EventRepository
from bot.repositories.task_repository import TaskRepository
from bot.repositories.user_repository import UserRepository
from bot.handlers.commands import run_start_flow
from bot.services.funnel_service import FunnelService
from bot.services.google_sheets_service import GoogleSheetsLeadService
from config.database import AsyncSessionLocal


logger = logging.getLogger(__name__)


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or update.effective_user is None or update.effective_chat is None:
        return

    await query.answer()

    google_sheets_service = GoogleSheetsLeadService()
    try:
        await google_sheets_service.sync_chat_id_by_username(
            update.effective_user.username,
            update.effective_chat.id,
        )
    except Exception:
        logger.exception(
            'Failed to sync Google Sheets chat_id by username from callback. username=%s chat_id=%s',
            update.effective_user.username,
            update.effective_chat.id,
        )

    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        funnel_service = FunnelService(context.bot, user_repository, event_repository, task_repository)
        data = query.data or ''
        user = await user_repository.get_by_telegram_id(update.effective_user.id)
        if data == 'trigger_start':
            await session.commit()
            await run_start_flow(update, context)
            return

        if user is None:
            await session.commit()
            await query.message.reply_text('Сначала нажми /start.')
            return

        if data == 'start_funnel':
            await funnel_service.start_funnel(user, context.application)
        elif data.startswith('goto_lesson:'):
            lesson_number = int(data.split(':')[1])
            await funnel_service.scheduler_service.cancel_tasks_for_user(user.id, TaskType.LESSON_FOLLOWUP)
            await funnel_service.send_lesson(user, lesson_number, context.application)
        elif data.startswith('watch_lesson:'):
            _, lesson_code, platform = data.split(':', 2)
            await event_repository.create(
                user.id,
                EventType.PLATFORM_CLICK.value,
                stage=lesson_code,
                payload={'platform': platform, 'lesson_code': lesson_code},
            )
            await funnel_service.send_platform_link(user, lesson_code, platform)
            await funnel_service.followup_service.schedule_lesson_followups(context.application, user, lesson_code)
        elif data == 'open_application':
            await funnel_service.open_application(user)
        await session.commit()
