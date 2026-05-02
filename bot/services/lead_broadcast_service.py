from __future__ import annotations

import logging
from datetime import time
from zoneinfo import ZoneInfo

from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import Application, CallbackContext

from bot.content.loader import get_lead_broadcast_config
from bot.keyboards.builders import build_application_keyboard, build_restart_funnel_keyboard
from bot.services.google_sheets_service import GoogleSheetsLeadService
from config.settings import get_settings


logger = logging.getLogger(__name__)

BROADCAST_TIMES = (
    time(hour=12, minute=0),
    time(hour=15, minute=0),
    time(hour=18, minute=0),
)

BROADCAST_TYPES = (
    'noon',
    'restart',
    'evening',
)


class LeadBroadcastService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.google_sheets_service = GoogleSheetsLeadService()
        self.config = get_lead_broadcast_config()

    def schedule_jobs(self, application: Application) -> None:
        logger.info('Lead broadcast scheduler init started')
        logger.info('Lead broadcast scheduler is disabled: daily broadcasts removed')
        return

    async def send_broadcast(self, application: Application, broadcast_type: str) -> None:
        logger.info('Lead broadcast started: type=%s', broadcast_type)

        message_text = self._get_message_by_type(broadcast_type)
        if not message_text:
            logger.warning('Lead broadcast was skipped: no broadcast message for type=%s', broadcast_type)
            return

        chat_ids = await self.google_sheets_service.read_all_chat_ids()
        logger.info('Lead broadcast total leads found: %s', len(chat_ids))

        if not chat_ids:
            logger.info('Lead broadcast was skipped: no valid chat_ids found in Google Sheets')
            return

        if broadcast_type == 'restart':
            reply_markup = build_restart_funnel_keyboard('Не откладывай')
        else:
            reply_markup = build_application_keyboard('Заполнить анкету')

        sent_count = 0
        failed_count = 0

        for chat_id in chat_ids:
            try:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    reply_markup=reply_markup,
                )
                sent_count += 1
            except (Forbidden, BadRequest) as exc:
                failed_count += 1
                logger.warning('Lead broadcast skipped for chat_id=%s: %s', chat_id, exc)
            except TelegramError as exc:
                failed_count += 1
                logger.exception('Lead broadcast failed for chat_id=%s: %s', chat_id, exc)

        logger.info(
            'Lead broadcast finished: sent=%s failed=%s total=%s',
            sent_count,
            failed_count,
            len(chat_ids),
        )

    def _get_message_by_type(self, broadcast_type: str) -> str:
        if broadcast_type == 'noon':
            return self.config.noon_message

        if broadcast_type == 'restart':
            return self.config.restart_message

        if broadcast_type == 'evening':
            return self.config.evening_message

        logger.warning('Lead broadcast was skipped: unsupported broadcast type=%s', broadcast_type)
        return ''


async def run_lead_broadcast(context: CallbackContext) -> None:
    service = LeadBroadcastService()
    broadcast_type = str(context.job.data.get('type', ''))
    await service.send_broadcast(context.application, broadcast_type)
