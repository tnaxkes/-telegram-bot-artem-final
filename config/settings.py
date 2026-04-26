from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_env: str = Field(default='development', alias='APP_ENV')
    app_host: str = Field(default='0.0.0.0', alias='APP_HOST')
    app_port: int = Field(default=8000, alias='APP_PORT')
    bot_token: str = Field(alias='BOT_TOKEN')
    database_url: str = Field(default='sqlite+aiosqlite:///./data/bot.db', alias='DATABASE_URL')
    timezone: str = Field(default='Europe/Moscow', alias='TIMEZONE')
    application_url: str = Field(
        default='https://docs.google.com/forms/d/e/1FAIpQLSd5A2QdSvPImL0I5etX1JRAuOMq5y_ah_Go05gIclFQ6tOsQg/viewform',
        alias='APPLICATION_URL',
    )
    admin_secret: str = Field(default='my-super-secret-admin-key-2026', alias='ADMIN_SECRET')
    log_level: str = Field(default='INFO', alias='LOG_LEVEL')
    google_sheet_id: str | None = Field(default=None, alias='GOOGLE_SHEET_ID')
    google_service_account_json: str | None = Field(default=None, alias='GOOGLE_SERVICE_ACCOUNT_JSON')

    @field_validator('google_sheet_id', 'google_service_account_json', mode='before')
    @classmethod
    def normalize_optional_env(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
