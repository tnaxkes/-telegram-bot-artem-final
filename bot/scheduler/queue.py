from urllib.parse import urlparse

from arq import create_pool
from arq.connections import RedisSettings

from config.settings import get_settings


settings = get_settings()


def get_redis_settings() -> RedisSettings:
    parsed = urlparse(settings.redis_url)
    return RedisSettings(
        host=parsed.hostname or 'localhost',
        port=parsed.port or 6379,
        database=int((parsed.path or '/0').replace('/', '') or 0),
        password=parsed.password,
    )


async def get_arq_pool():
    return await create_pool(get_redis_settings())
