from functools import lru_cache
from pathlib import Path

import yaml

from bot.models.content import FunnelConfig, LeadBroadcastConfig
from config.settings import get_settings


CONTENT_FILE = Path(__file__).resolve().parent / 'funnel.yaml'
LEAD_BROADCASTS_FILE = Path(__file__).resolve().parent / 'lead_broadcasts.yaml'


@lru_cache(maxsize=1)
def get_funnel_config() -> FunnelConfig:
    with CONTENT_FILE.open('r', encoding='utf-8') as file:
        raw = yaml.safe_load(file)
    config = FunnelConfig.model_validate(raw)
    settings = get_settings()
    if config.application_buttons:
        config.application_buttons[0].url = settings.application_url
    return config


@lru_cache(maxsize=1)
def get_lead_broadcast_config() -> LeadBroadcastConfig:
    with LEAD_BROADCASTS_FILE.open('r', encoding='utf-8') as file:
        raw = yaml.safe_load(file) or {}
    return LeadBroadcastConfig.model_validate(raw)
