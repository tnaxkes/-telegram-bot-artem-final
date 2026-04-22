from telegram import Update
from telegram.ext import ContextTypes

from bot.models.enums import EventType, TaskType
from bot.repositories.event_repository import EventRepository
from bot.repositories.task_repository import TaskRepository
from bot.repositories.user_repository import UserRepository
from bot.services.funnel_service import FunnelService
from config.database import AsyncSessionLocal


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or update.effective_user is None:
        return

    await query.answer()

    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        funnel_service = FunnelService(context.bot, user_repository, event_repository, task_repository)
        user = await user_repository.get_by_telegram_id(update.effective_user.id)
        if user is None:
            await session.commit()
            await query.message.reply_text('Сначала нажми /start.')
            return

        data = query.data or ''
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
