from redis.asyncio import Redis

from config.settings import get_settings


_settings = get_settings()


def get_redis() -> Redis:
    return Redis.from_url(_settings.redis_url, decode_responses=True)
