import logging

from telegram import BotCommand
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from bot.handlers.callbacks import callback_router
from bot.handlers.commands import manager_command, start_command, stop_command, submit_application_command
from bot.repositories.event_repository import EventRepository
from bot.repositories.task_repository import TaskRepository
from bot.services.lead_broadcast_service import LeadBroadcastService
from bot.scheduler.tasks import run_scheduled_task
from bot.services.scheduler_service import SchedulerService
from config.database import AsyncSessionLocal, init_db
from config.logging import setup_logging
from config.settings import get_settings


logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    await init_db()
    await application.bot.set_my_commands([
        BotCommand('start', 'Запустить бота заново'),
        BotCommand('manager', 'Связь с менеджером'),
    ])
    application.bot_data['scheduled_task_callback'] = run_scheduled_task
    LeadBroadcastService().schedule_jobs(application)
    async with AsyncSessionLocal() as session:
        scheduler = SchedulerService(TaskRepository(session), EventRepository(session))
        count = await scheduler.recover_pending_tasks(application)
        await session.commit()
        logger.info('Recovered %s pending local tasks', count)


def run_bot() -> None:
    setup_logging()
    settings = get_settings()

    application = Application.builder().token(settings.bot_token).post_init(post_init).build()
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('manager', manager_command))
    application.add_handler(CommandHandler('stop', stop_command))
    application.add_handler(CommandHandler('submit_application', submit_application_command))
    application.add_handler(CallbackQueryHandler(callback_router))

    logger.info('Starting Telegram bot polling in local mode')
    application.run_polling(drop_pending_updates=False)
