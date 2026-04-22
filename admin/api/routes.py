from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from admin.api.schemas import ApplicationCompleteRequest, ManualMessageRequest, MoveStageRequest, UserResponse
from bot.content.loader import get_funnel_config
from bot.keyboards.builders import build_application_keyboard
from bot.repositories.event_repository import EventRepository
from bot.repositories.task_repository import TaskRepository
from bot.repositories.user_repository import UserRepository
from bot.services.funnel_service import FunnelService
from bot.services.message_service import MessageService
from config.database import AsyncSessionLocal
from config.settings import get_settings


templates = Jinja2Templates(directory='admin/templates')
settings = get_settings()
admin_router = APIRouter(tags=['admin'])


KNOWN_STATUSES = [
    'new',
    'started',
    'lesson_1_opened',
    'lesson_1_followup_sent',
    'lesson_2_opened',
    'lesson_3_opened',
    'offer_sent',
    'application_opened',
    'application_submitted',
    'lost',
    'completed',
]


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def pct(part: int, total: int) -> str:
    if total <= 0:
        return '0%'
    return f'{round((part / total) * 100)}%'


async def require_admin(request: Request) -> None:
    secret = request.headers.get('x-admin-secret') or request.query_params.get('secret')
    if secret != settings.admin_secret:
        raise HTTPException(status_code=401, detail='Unauthorized')


async def build_dashboard_payload() -> dict:
    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        users = await user_repository.list_users()
        all_tasks = []
        for user in users:
            all_tasks.extend(await task_repository.list_for_user(user.id))

        total_users = len(users)
        lesson_1_reached = sum(1 for user in users if user.current_lesson >= 1 or user.status in {'lesson_1_opened', 'lesson_1_followup_sent', 'lesson_2_opened', 'lesson_3_opened', 'offer_sent', 'application_opened', 'application_submitted'})
        lesson_2_reached = sum(1 for user in users if user.lesson_2_reached)
        lesson_3_reached = sum(1 for user in users if user.lesson_3_reached)
        offer_seen = sum(1 for user in users if user.current_stage == 'application_offer' or user.application_opened or user.application_submitted or user.status in {'offer_sent', 'application_opened', 'application_submitted'})
        application_opened = sum(1 for user in users if user.application_opened)
        application_submitted = sum(1 for user in users if user.application_submitted)
        unsubscribed = sum(1 for user in users if user.unsubscribed)

        status_counts = Counter(user.status for user in users)
        stage_counts = Counter(user.current_stage for user in users)
        task_status_counts = Counter(task.status for task in all_tasks)

        stuck_before_lesson_2 = [
            user for user in users
            if user.current_lesson == 1 and not user.lesson_2_reached and not user.application_submitted and not user.unsubscribed
        ][:10]
        stuck_before_lesson_3 = [
            user for user in users
            if user.current_lesson == 2 and not user.lesson_3_reached and not user.application_submitted and not user.unsubscribed
        ][:10]
        stuck_on_offer = [
            user for user in users
            if (user.current_stage == 'application_offer' or user.application_opened or user.status in {'offer_sent', 'application_opened'})
            and not user.application_submitted
            and not user.unsubscribed
        ][:10]

        recent_events = await event_repository.list_recent(limit=15)
        recent_user_map = {user.id: user for user in users}

        return {
            'total_users': total_users,
            'lesson_1_reached': lesson_1_reached,
            'lesson_2_reached': lesson_2_reached,
            'lesson_3_reached': lesson_3_reached,
            'offer_seen': offer_seen,
            'application_opened': application_opened,
            'application_submitted': application_submitted,
            'unsubscribed': unsubscribed,
            'status_counts': {status: status_counts.get(status, 0) for status in KNOWN_STATUSES if status_counts.get(status, 0)},
            'stage_counts': dict(stage_counts),
            'task_status_counts': dict(task_status_counts),
            'recent_users': users[:10],
            'funnel_rows': [
                {'label': 'Старт', 'count': total_users, 'rate': '100%'},
                {'label': '1 урок', 'count': lesson_1_reached, 'rate': pct(lesson_1_reached, total_users)},
                {'label': '2 урок', 'count': lesson_2_reached, 'rate': pct(lesson_2_reached, total_users)},
                {'label': '3 урок', 'count': lesson_3_reached, 'rate': pct(lesson_3_reached, total_users)},
                {'label': 'Оффер', 'count': offer_seen, 'rate': pct(offer_seen, total_users)},
                {'label': 'Анкета открыта', 'count': application_opened, 'rate': pct(application_opened, total_users)},
                {'label': 'Заявка', 'count': application_submitted, 'rate': pct(application_submitted, total_users)},
            ],
            'stuck_before_lesson_2': stuck_before_lesson_2,
            'stuck_before_lesson_3': stuck_before_lesson_3,
            'stuck_on_offer': stuck_on_offer,
            'recent_events': [
                {
                    'event': event,
                    'user': recent_user_map.get(event.user_id),
                }
                for event in recent_events
            ],
        }


@admin_router.get('/', dependencies=[Depends(require_admin)])
async def root_redirect(request: Request):
    secret = request.query_params.get('secret', '')
    return RedirectResponse(f'/admin/dashboard?secret={secret}', status_code=302)


@admin_router.get('/api/admin/dashboard', dependencies=[Depends(require_admin)])
async def api_dashboard():
    return await build_dashboard_payload()


@admin_router.get('/api/admin/users', dependencies=[Depends(require_admin)])
async def api_list_users(
    status: str | None = None,
    source: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    q: str | None = None,
):
    async with AsyncSessionLocal() as session:
        repository = UserRepository(session)
        users = await repository.list_users(
            status=status,
            source=source,
            created_from=parse_dt(created_from),
            created_to=parse_dt(created_to),
        )
        if q:
            query = q.lower().strip()
            users = [
                user for user in users
                if query in str(user.telegram_id).lower()
                or query in (user.username or '').lower()
                or query in (user.first_name or '').lower()
            ]
        return [UserResponse.from_model(user).model_dump() for user in users]


@admin_router.get('/api/admin/users/{user_id}', dependencies=[Depends(require_admin)])
async def api_user_detail(user_id: int):
    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        user = await user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail='User not found')
        return {
            'user': UserResponse.from_model(user).model_dump(),
            'events': [
                {
                    'id': event.id,
                    'event_type': event.event_type,
                    'stage': event.stage,
                    'payload': event.payload,
                    'created_at': event.created_at,
                }
                for event in await event_repository.list_for_user(user_id)
            ],
            'tasks': [
                {
                    'id': task.id,
                    'task_type': task.task_type,
                    'status': task.status,
                    'dedup_key': task.dedup_key,
                    'run_at': task.run_at,
                    'sent_at': task.sent_at,
                    'payload': task.payload,
                }
                for task in await task_repository.list_for_user(user_id)
            ],
        }


@admin_router.post('/api/admin/users/{user_id}/move-stage', dependencies=[Depends(require_admin)])
async def api_move_stage(request: Request, user_id: int, body: MoveStageRequest):
    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        funnel_service = FunnelService(request.app.state.bot, user_repository, event_repository, task_repository)
        user = await user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail='User not found')

        stage = body.stage
        if stage.startswith('lesson_'):
            lesson_number = int(stage.split('_')[1])
            await user_repository.set_stage(user, stage, lesson=lesson_number)
            if body.send_message:
                await funnel_service.send_lesson(user, lesson_number)
        elif stage == 'application_offer':
            await user_repository.set_stage(user, stage)
            if body.send_message:
                await funnel_service.send_offer(user)
        else:
            await user_repository.set_stage(user, stage)
        await event_repository.create(user.id, 'manual_action', stage=stage, payload={'action': 'move_stage'})
        await session.commit()
        return {'ok': True, 'stage': stage}


@admin_router.post('/api/admin/users/{user_id}/stop', dependencies=[Depends(require_admin)])
async def api_stop_user(request: Request, user_id: int):
    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        funnel_service = FunnelService(request.app.state.bot, user_repository, event_repository, task_repository)
        user = await user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail='User not found')
        await user_repository.stop_user(user)
        await funnel_service.scheduler_service.cancel_tasks_for_user(user.id)
        await event_repository.create(user.id, 'manual_action', stage=user.current_stage, payload={'action': 'stop'})
        await session.commit()
        return {'ok': True}


@admin_router.post('/api/admin/users/{user_id}/manual-message', dependencies=[Depends(require_admin)])
async def api_manual_message(request: Request, user_id: int, body: ManualMessageRequest):
    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        user = await user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail='User not found')
        message_service = MessageService(request.app.state.bot)
        funnel = get_funnel_config()
        text = body.text or (funnel.followup_texts.get(body.message_code) if body.message_code else None)
        if not text:
            raise HTTPException(status_code=400, detail='Text or valid message_code required')
        reply_markup = build_application_keyboard() if body.with_application_button else None
        await message_service.send_text(user.telegram_id, text, reply_markup)
        await event_repository.create(
            user.id,
            'manual_action',
            stage=user.current_stage,
            payload={'action': 'manual_message', 'message_code': body.message_code, 'text': body.text},
        )
        await session.commit()
        return {'ok': True}


@admin_router.post('/api/applications/complete', dependencies=[Depends(require_admin)])
async def api_application_complete(request: Request, body: ApplicationCompleteRequest):
    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        funnel_service = FunnelService(request.app.state.bot, user_repository, event_repository, task_repository)
        user = None
        if body.user_id is not None:
            user = await user_repository.get_by_id(body.user_id)
        elif body.telegram_id is not None:
            user = await user_repository.get_by_telegram_id(body.telegram_id)
        if user is None:
            raise HTTPException(status_code=404, detail='User not found')
        await funnel_service.handle_application_submitted(user)
        await event_repository.create(
            user.id,
            'manual_action',
            stage='application_submitted',
            payload={'action': 'application_complete', 'note': body.note},
        )
        await session.commit()
        return {'ok': True, 'user_id': user.id}


@admin_router.get('/admin/dashboard', response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_dashboard_page(request: Request):
    payload = await build_dashboard_payload()
    return templates.TemplateResponse(
        'dashboard.html',
        {
            'request': request,
            'secret': request.query_params.get('secret', ''),
            **payload,
        },
    )


@admin_router.get('/admin/users', response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_users_page(
    request: Request,
    status: str | None = None,
    source: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    q: str | None = None,
):
    async with AsyncSessionLocal() as session:
        repository = UserRepository(session)
        users = await repository.list_users(
            status=status,
            source=source,
            created_from=parse_dt(created_from),
            created_to=parse_dt(created_to),
        )
        if q:
            query = q.lower().strip()
            users = [
                user for user in users
                if query in str(user.telegram_id).lower()
                or query in (user.username or '').lower()
                or query in (user.first_name or '').lower()
            ]
        return templates.TemplateResponse(
            'users.html',
            {
                'request': request,
                'users': users,
                'filters': {
                    'status': status or '',
                    'source': source or '',
                    'created_from': created_from or '',
                    'created_to': created_to or '',
                    'q': q or '',
                },
                'secret': request.query_params.get('secret', ''),
                'known_statuses': KNOWN_STATUSES,
            },
        )


@admin_router.get('/admin/users/{user_id}', response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_user_detail_page(request: Request, user_id: int):
    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        event_repository = EventRepository(session)
        task_repository = TaskRepository(session)
        user = await user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail='User not found')
        return templates.TemplateResponse(
            'user_detail.html',
            {
                'request': request,
                'user': user,
                'events': await event_repository.list_for_user(user_id),
                'tasks': await task_repository.list_for_user(user_id),
                'secret': request.query_params.get('secret', ''),
                'known_statuses': KNOWN_STATUSES,
                'message_codes': sorted(get_funnel_config().followup_texts.keys()),
            },
        )
