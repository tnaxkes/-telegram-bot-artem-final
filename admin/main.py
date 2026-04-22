from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from telegram import Bot

from admin.api.routes import admin_router
from config.database import init_db
from config.logging import setup_logging
from config.settings import get_settings


setup_logging()
settings = get_settings()
app = FastAPI(title='Funnel Admin')
app.mount('/static', StaticFiles(directory='admin/static'), name='static')
app.include_router(admin_router)


@app.on_event('startup')
async def startup() -> None:
    await init_db()
    bot = Bot(token=settings.bot_token)
    await bot.initialize()
    app.state.bot = bot


@app.on_event('shutdown')
async def shutdown() -> None:
    await app.state.bot.shutdown()


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}
