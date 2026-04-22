from telegram import Update
from telegram.ext import ContextTypes

from bot.models.enums import EventType
from bot.repositories.event_repository import EventRepository
from bot.repositories.task_repository import TaskRepository
from bot.repositories.user_repository import UserRepository
from bot.services.funnel_service import FunnelService
from config.database import AsyncSessionLocal


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.effective_chat is None or update.message is None:
        return

    source = context.args[0] if context.args else None

    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        funnel_service = FunnelService(context.bot, user_repository, event_repository, task_repository)

        user, created = await user_repository.create_or_update_from_telegram(
            telegram_id=update.effective_user.id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
            last_name=update.effective_user.last_name,
            source=source,
        )
        if created:
            await event_repository.create(user.id, EventType.USER_CREATED.value, stage='start', payload={'source': source})
        await funnel_service.scheduler_service.cancel_tasks_for_user(user.id)
        await funnel_service.send_start(user)
        await funnel_service.start_funnel(user, context.application)
        await session.commit()


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        funnel_service = FunnelService(context.bot, user_repository, event_repository, task_repository)
        user = await user_repository.get_by_telegram_id(update.effective_user.id)
        if user is None:
            await update.message.reply_text('Пользователь не найден. Нажми /start заново.')
            return
        await user_repository.stop_user(user)
        await funnel_service.scheduler_service.cancel_tasks_for_user(user.id)
        await event_repository.create(user.id, EventType.MANUAL_ACTION.value, stage=user.current_stage, payload={'action': 'stop'})
        await session.commit()
        await update.message.reply_text('Цепочка остановлена. Если захочешь вернуться, нажми /start.')


async def submit_application_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        funnel_service = FunnelService(context.bot, user_repository, event_repository, task_repository)
        user = await user_repository.get_by_telegram_id(update.effective_user.id)
        if user is None:
            await update.message.reply_text('Сначала нажми /start.')
            return
        await funnel_service.handle_application_submitted(user)
        await event_repository.create(user.id, EventType.MANUAL_ACTION.value, stage='application_submitted', payload={'action': 'submit_application_command'})
        await session.commit()



async def manager_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_text('Для связи с менеджером напиши: @yurow_work')
