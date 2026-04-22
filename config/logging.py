import logging

from config.settings import get_settings


LOG_FORMAT = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'


def setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=LOG_FORMAT,
    )
