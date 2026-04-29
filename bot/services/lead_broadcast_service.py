from __future__ import annotations

import logging
from datetime import time
from zoneinfo import ZoneInfo

from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import Application, CallbackContext

from bot.content.loader import get_lead_broadcast_config
from bot.keyboards.builders import build_application_keyboard
from bot.services.google_sheets_service import GoogleSheetsLeadService
from config.settings import get_settings


logger = logging.getLogger(__name__)

BROADCAST_TIMES = (
    time(hour=1, minute=50),
    time(hour=23, minute=45),
)


class LeadBroadcastService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.google_sheets_service = GoogleSheetsLeadService()
        self.config = get_lead_broadcast_config()

    def schedule_jobs(self, application: Application) -> None:
        logger.info('Lead broadcast scheduler init started')

        configuration_error = self.google_sheets_service.get_configuration_error()
        if configuration_error is not None:
            logger.warning('Lead broadcast scheduler is disabled: %s', configuration_error)
            return

        if not self.config.noon_message or not self.config.evening_message:
            logger.warning('Lead broadcast scheduler is disabled: no lead broadcast messages configured')
            return

        if application.job_queue is None:
            logger.error('Lead broadcast scheduler is disabled: application.job_queue is None')
            return

        timezone = ZoneInfo(self.settings.timezone)

        for scheduled_time in BROADCAST_TIMES:
            application.job_queue.run_daily(
                callback=run_lead_broadcast,
                time=scheduled_time.replace(tzinfo=timezone),
                name=f'lead-broadcast-{scheduled_time.hour:02d}-{scheduled_time.minute:02d}',
                data={'broadcast_hour': scheduled_time.hour},
            )
            logger.info('Lead broadcast job registered: %s (%s)', scheduled_time, self.settings.timezone)

        logger.info(
            'Scheduled lead broadcasts at %s and %s (%s)',
            BROADCAST_TIMES[0],
            BROADCAST_TIMES[1],
            self.settings.timezone,
        )

    async def send_broadcast(self, application: Application, broadcast_hour: int) -> None:
        logger.info('Lead broadcast started: hour=%s', broadcast_hour)

        message_text = self._get_message_for_hour(broadcast_hour)
        if not message_text:
            logger.warning('Lead broadcast was skipped: no broadcast message for hour=%s', broadcast_hour)
            return

        chat_ids = await self.google_sheets_service.read_all_chat_ids()
        logger.info('Lead broadcast total leads found: %s', len(chat_ids))

        if not chat_ids:
            logger.info('Lead broadcast was skipped: no valid chat_ids found in Google Sheets')
            return

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

    def _get_message_for_hour(self, broadcast_hour: int) -> str:
        if broadcast_hour == 1:
            return self.config.noon_message

        if broadcast_hour == 23:
            return self.config.evening_message

        logger.warning('Lead broadcast was skipped: unsupported broadcast hour=%s', broadcast_hour)
        return ''


async def run_lead_broadcast(context: CallbackContext) -> None:
    service = LeadBroadcastService()
    broadcast_hour = int(context.job.data.get('broadcast_hour', 0))
    await service.send_broadcast(context.application, broadcast_hour) 
