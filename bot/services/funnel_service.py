from __future__ import annotations

from telegram import Bot
from telegram.ext import Application

from bot.content.loader import get_funnel_config
from bot.keyboards.builders import (
    build_application_keyboard,
    build_external_url_keyboard,
    build_next_lesson_keyboard,
    build_platform_keyboard,
    build_start_keyboard,
)
from bot.models.db import User
from bot.models.enums import EventType, TaskType, UserStatus
from bot.repositories.event_repository import EventRepository
from bot.repositories.task_repository import TaskRepository
from bot.repositories.user_repository import UserRepository
from bot.services.event_service import EventService
from bot.services.followup_service import FollowupService
from bot.services.message_service import MessageService
from bot.services.scheduler_service import SchedulerService


class FunnelService:
    def __init__(self, bot: Bot, user_repository: UserRepository, event_repository: EventRepository, task_repository: TaskRepository):
        self.bot = bot
        self.user_repository = user_repository
        self.event_repository = event_repository
        self.task_repository = task_repository
        self.event_service = EventService(event_repository)
        self.scheduler_service = SchedulerService(task_repository, event_repository)
        self.followup_service = FollowupService(self.scheduler_service)
        self.message_service = MessageService(bot)
        self.funnel = get_funnel_config()

    async def send_start(self, user: User) -> None:
        step = self.funnel.steps['start']
        start_text = step.body if not step.title else f'{step.title}\n\n{step.body}'
        await self.message_service.send_start_media(
            chat_id=user.telegram_id,
            file_id=self.funnel.start_video_file_id,
            fallback_text=start_text,
        )

    async def start_funnel(self, user: User, application: Application | None = None) -> None:
        await self.scheduler_service.cancel_tasks_for_user(user.id, TaskType.LESSON_FOLLOWUP)
        await self.user_repository.update_status(user, UserStatus.STARTED, stage='lesson_1')
        await self.send_lesson(user, 1, application)
        if application is not None:
            await self.followup_service.schedule_lesson_followups(application, user, 'lesson_1')
        await self.event_service.log(user.id, EventType.STARTED, stage='lesson_1')

    async def send_lesson(self, user: User, lesson_number: int, application: Application | None = None) -> None:
        lesson_code = f'lesson_{lesson_number}'
        step = self.funnel.steps[lesson_code]
        await self.user_repository.set_stage(user, lesson_code, lesson=lesson_number)
        if lesson_number == 1:
            await self.user_repository.update_status(user, UserStatus.LESSON_1_OPENED, stage=lesson_code)
        elif lesson_number == 2:
            await self.user_repository.update_status(user, UserStatus.LESSON_2_OPENED, stage=lesson_code)
        elif lesson_number == 3:
            await self.user_repository.update_status(user, UserStatus.LESSON_3_OPENED, stage=lesson_code)
        await self.message_service.send_step(user.telegram_id, step, build_platform_keyboard(step))
        if application is not None and lesson_number in {2, 3}:
            await self.scheduler_service.cancel_tasks_for_user(user.id, TaskType.LESSON_FOLLOWUP)
            await self.followup_service.schedule_lesson_followups(application, user, lesson_code)
        await self.event_service.log(user.id, EventType.LESSON_SENT, stage=lesson_code, payload={'lesson_number': lesson_number})

    async def send_offer(self, user: User, application: Application | None = None) -> None:
        step = self.funnel.steps['application_offer']
        await self.user_repository.update_status(user, UserStatus.OFFER_SENT, stage='application_offer')
        await self.scheduler_service.cancel_tasks_for_user(user.id, TaskType.APPLICATION_FOLLOWUP)
        await self.message_service.send_step(user.telegram_id, step, build_application_keyboard(step.cta_text or 'хочу зарабатывать'))
        await self.event_service.log(user.id, EventType.OFFER_SENT, stage='application_offer')
        if application is not None and not user.application_submitted and not user.unsubscribed:
            await self.followup_service.schedule_application_followups(application, user)

    async def send_followup_message(self, user: User, message_code: str, next_step: str | None = None, application: Application | None = None) -> None:
        text = self.funnel.followup_texts[message_code]
        reply_markup = None
        if next_step == 'lesson_2':
            reply_markup = build_next_lesson_keyboard(2)
        elif next_step == 'lesson_3':
            reply_markup = build_next_lesson_keyboard(3)
        elif message_code.startswith('application_followup'):
            reply_markup = build_application_keyboard(self.funnel.steps['application_offer'].cta_text or 'хочу зарабатывать')
        if message_code == 'lesson_2_nudge_1':
            await self.message_service.send_lesson_2_nudge_1_video(user.telegram_id, text, reply_markup)
        elif message_code == 'lesson_2_nudge_2':
            await self.message_service.send_lesson_2_nudge_2_photo(user.telegram_id, text, reply_markup)
        elif message_code == 'lesson_2_nudge_3':
            await self.message_service.send_lesson_2_nudge_3_photo(user.telegram_id, text, reply_markup)
        else:
            await self.message_service.send_text(user.telegram_id, text, reply_markup)
        if message_code == 'lesson_1_followup' and application is not None:
            await self.followup_service.schedule_next_lesson_nudges(application, user, 2)
        elif message_code == 'lesson_2_followup' and application is not None:
            await self.followup_service.schedule_next_lesson_nudges(application, user, 3)
        if message_code.startswith('lesson_1'):
            await self.user_repository.update_status(user, UserStatus.LESSON_1_FOLLOWUP_SENT, stage=user.current_stage)
        await self.event_service.log(user.id, EventType.FOLLOWUP_SENT, stage=user.current_stage, payload={'message_code': message_code})

    async def send_platform_link(self, user: User, lesson_code: str, platform: str) -> None:
        step = self.funnel.steps[lesson_code]
        link = next((item for item in step.platforms if item.platform == platform), None)
        if link is None:
            return
        await self.message_service.send_text(
            user.telegram_id,
            f'Смотри урок на {platform.upper()} по кнопке ниже.',
            build_external_url_keyboard(link.label, link.url),
        )

    async def open_application(self, user: User) -> None:
        await self.user_repository.mark_application_opened(user)
        await self.scheduler_service.cancel_tasks_for_user(user.id, TaskType.APPLICATION_FOLLOWUP)
        await self.event_service.log(user.id, EventType.APPLICATION_OPENED, stage='application_offer')
        url = self.funnel.application_buttons[0].url if self.funnel.application_buttons else 'https://example.com'
        await self.message_service.send_text(
            user.telegram_id,
            'Анкета ниже. Если тебе это реально нужно — заполни сейчас.',
            build_external_url_keyboard('Заполнить анкету', url),
        )

    async def handle_application_submitted(self, user: User) -> None:
        await self.user_repository.mark_application_submitted(user)
        await self.scheduler_service.cancel_tasks_for_user(user.id, task_type=None)
        await self.event_service.log(user.id, EventType.APPLICATION_SUBMITTED, stage='application_submitted')
        await self.message_service.send_text(user.telegram_id, 'Заявка зафиксирована. Дожимы остановлены.')
