from telegram import Bot

from bot.scheduler.queue import get_redis_settings
from bot.scheduler.tasks import send_scheduled_task
from config.logging import setup_logging
from config.settings import get_settings


async def startup(ctx):
    setup_logging()
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    await bot.initialize()
    ctx['bot'] = bot


async def shutdown(ctx):
    bot: Bot = ctx['bot']
    await bot.shutdown()


class WorkerSettings:
    functions = [send_scheduled_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = get_redis_settings()
