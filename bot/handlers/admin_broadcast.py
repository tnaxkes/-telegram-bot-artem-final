from __future__ import annotations

import logging

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import ContextTypes

from bot.services.google_sheets_service import GoogleSheetsLeadService
from config.settings import get_settings


logger = logging.getLogger(__name__)

BROADCAST_BUTTON_TEXT = 'Рассылка'
AWAITING_BROADCAST_TEXT_KEY = 'awaiting_broadcast_text'


def _build_admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BROADCAST_BUTTON_TEXT)]],
        resize_keyboard=True,
    )


def _is_admin(update: Update) -> bool:
    if update.effective_chat is None:
        return False
    settings = get_settings()
    return settings.admin_chat_id is not None and update.effective_chat.id == settings.admin_chat_id


async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not _is_admin(update):
        return

    await update.message.reply_text(
        'Админ-панель. Нажми "Рассылка", чтобы отправить сообщение по всем chat_id из таблицы.',
        reply_markup=_build_admin_keyboard(),
    )


async def admin_broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.message.text is None or not _is_admin(update):
        return

    message_text = update.message.text.strip()

    if message_text == BROADCAST_BUTTON_TEXT:
        context.user_data[AWAITING_BROADCAST_TEXT_KEY] = True
        await update.message.reply_text('Отправь сообщение для рассылки')
        return

    if not context.user_data.get(AWAITING_BROADCAST_TEXT_KEY):
        return

    context.user_data[AWAITING_BROADCAST_TEXT_KEY] = False
    await update.message.reply_text('Начинаю рассылку...')

    sent_count, failed_count = await _send_manual_broadcast(context, message_text)

    await update.message.reply_text(
        f'Рассылка завершена: отправлено {sent_count}, ошибок {failed_count}',
        reply_markup=_build_admin_keyboard(),
    )


async def _send_manual_broadcast(context: ContextTypes.DEFAULT_TYPE, message_text: str) -> tuple[int, int]:
    google_sheets_service = GoogleSheetsLeadService()
    chat_ids = await google_sheets_service.read_all_chat_ids()
    logger.info('Manual admin broadcast started: total chat_ids=%s', len(chat_ids))

    sent_count = 0
    failed_count = 0

    for chat_id in chat_ids:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message_text)
            sent_count += 1
        except (Forbidden, BadRequest) as exc:
            failed_count += 1
            logger.warning('Manual admin broadcast skipped for chat_id=%s: %s', chat_id, exc)
        except TelegramError as exc:
            failed_count += 1
            logger.exception('Manual admin broadcast failed for chat_id=%s: %s', chat_id, exc)

    logger.info(
        'Manual admin broadcast finished: sent=%s failed=%s total=%s',
        sent_count,
        failed_count,
        len(chat_ids),
    )
    return sent_count, failed_count
