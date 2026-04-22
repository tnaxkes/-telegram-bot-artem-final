import uvicorn

from admin.main import app
from config.settings import get_settings


if __name__ == '__main__':
    settings = get_settings()
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
