from bot.models.enums import EventType
from bot.repositories.event_repository import EventRepository
from bot.repositories.task_repository import TaskRepository
from bot.repositories.user_repository import UserRepository
from bot.services.followup_service import FollowupService
from bot.services.funnel_service import FunnelService


class TrackingService:
    def __init__(self, funnel_service: FunnelService, user_repository: UserRepository, event_repository: EventRepository, task_repository: TaskRepository):
        self.funnel_service = funnel_service
        self.user_repository = user_repository
        self.event_repository = event_repository
        self.task_repository = task_repository
        self.followup_service = FollowupService(funnel_service.scheduler_service)

    async def process_lesson_click(self, user_id: int, lesson_code: str, platform: str) -> str:
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise ValueError('User not found')
        step = self.funnel_service.funnel.steps[lesson_code]
        target = next((link.url for link in step.platforms if link.platform == platform), None)
        if not target:
            raise ValueError('Platform not found')
        await self.event_repository.create(
            user_id=user.id,
            event_type=EventType.PLATFORM_CLICK.value,
            stage=lesson_code,
            payload={'platform': platform, 'lesson_code': lesson_code, 'target': target},
        )
        await self.followup_service.schedule_lesson_followups(user, lesson_code)
        return target

    async def process_application_click(self, user_id: int) -> str:
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise ValueError('User not found')
        await self.user_repository.mark_application_opened(user)
        await self.event_repository.create(
            user_id=user.id,
            event_type=EventType.APPLICATION_OPENED.value,
            stage='application_offer',
            payload={'application_url': self.funnel_service.funnel.application_buttons[0].url if self.funnel_service.funnel.application_buttons else None},
        )
        await self.funnel_service.send_application_hint(user)
        if not user.application_submitted and not user.unsubscribed:
            await self.followup_service.schedule_application_followups(user)
        return self.funnel_service.funnel.application_buttons[0].url
