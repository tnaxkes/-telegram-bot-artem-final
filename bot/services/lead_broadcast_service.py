from __future__ import annotations

import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import Application, CallbackContext

from bot.content.loader import get_lead_broadcast_config
from bot.keyboards.builders import build_application_keyboard
from bot.services.google_sheets_service import GoogleSheetsLeadService
from config.settings import get_settings


logger = logging.getLogger(__name__)
CAMPAIGN_RUN_TIME = time(hour=19, minute=29)


class LeadBroadcastService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.google_sheets_service = GoogleSheetsLeadService()
        self.config = get_lead_broadcast_config()

    def schedule_jobs(self, application: Application) -> None:
        logger.info('Lead broadcast scheduler init started')

        if not self.config.campaign_posts:
            logger.warning('Lead broadcast scheduler is disabled: no campaign posts configured')
            return

        if application.job_queue is None:
            logger.error('Lead broadcast scheduler is disabled: application.job_queue is None')
            return

        timezone = ZoneInfo(self.settings.timezone)
        now = datetime.now(timezone)
        registered_posts = 0

        for campaign_post in self.config.campaign_posts:
            scheduled_at = datetime.combine(campaign_post.date, CAMPAIGN_RUN_TIME, tzinfo=timezone)
            if scheduled_at <= now:
                logger.info('Lead broadcast campaign post skipped at startup: date=%s time=%s already passed', campaign_post.date, CAMPAIGN_RUN_TIME)
                continue

            application.job_queue.run_once(
                callback=run_lead_broadcast,
                when=scheduled_at,
                name=f'lead-broadcast-campaign-{campaign_post.date.isoformat()}',
                data={'campaign_date': campaign_post.date.isoformat()},
            )
            registered_posts += 1
            logger.info(
                'Lead broadcast job registered: campaign_date=%s time=%s (%s)',
                campaign_post.date,
                CAMPAIGN_RUN_TIME,
                self.settings.timezone,
            )

        logger.info('Lead broadcast campaign jobs registered: %s', registered_posts)

    async def send_broadcast(self, application: Application, campaign_date: str) -> None:
        logger.info('Lead broadcast started: campaign_date=%s', campaign_date)

        campaign_post = self._get_campaign_post_by_date(campaign_date)
        if campaign_post is None:
            logger.info('Lead broadcast was skipped: no campaign post for date=%s', campaign_date)
            return

        chat_ids = await self.google_sheets_service.read_all_chat_ids()
        logger.info('Lead broadcast total leads found: %s', len(chat_ids))

        if not chat_ids:
            logger.info('Lead broadcast was skipped: no valid chat_ids found in Google Sheets')
            return

        reply_markup = build_application_keyboard(campaign_post.button_text)

        sent_count = 0
        failed_count = 0

        for chat_id in chat_ids:
            try:
                await application.bot.send_video(
                    chat_id=chat_id,
                    video=campaign_post.video_file_id,
                    caption=campaign_post.text,
                    reply_markup=reply_markup,
                    write_timeout=8,
                    read_timeout=12,
                    connect_timeout=6,
                    pool_timeout=6,
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

    def _get_campaign_post_by_date(self, campaign_date: str):
        for campaign_post in self.config.campaign_posts:
            if campaign_post.date.isoformat() == campaign_date:
                return campaign_post
        return None


async def run_lead_broadcast(context: CallbackContext) -> None:
    service = LeadBroadcastService()
    campaign_date = str(context.job.data.get('campaign_date', ''))
    await service.send_broadcast(context.application, campaign_date)
