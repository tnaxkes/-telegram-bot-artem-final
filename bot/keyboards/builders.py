from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.content import FunnelStep
from config.settings import get_settings


PLATFORM_LABELS = {
    'youtube': 'Смотреть в YouTube',
    'vk': 'Смотреть в VK',
    'rutube': 'Смотреть в RuTube',
}


def build_start_keyboard(step: FunnelStep) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(step.cta_text or 'Поехали', callback_data=step.cta_callback or 'start_funnel')]])


def build_next_lesson_keyboard(lesson_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(f'Смотреть {lesson_number} урок', callback_data=f'goto_lesson:{lesson_number}')]])


def build_platform_keyboard(step: FunnelStep) -> InlineKeyboardMarkup:
    buttons = []
    direct_links = bool(step.metadata.get('direct_links'))
    for link in step.platforms:
        label = PLATFORM_LABELS.get(link.platform, link.label)
        if direct_links:
            buttons.append([InlineKeyboardButton(label, url=link.url)])
        else:
            buttons.append([InlineKeyboardButton(label, callback_data=f'watch_lesson:{step.code}:{link.platform}')])
    return InlineKeyboardMarkup(buttons)


def build_external_url_keyboard(label: str, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, url=url)]])


def build_application_keyboard(label: str = 'хочу зарабатывать') -> InlineKeyboardMarkup:
    settings = get_settings()
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, url=settings.application_url)]])
