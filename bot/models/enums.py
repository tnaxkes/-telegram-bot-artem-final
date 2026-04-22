from enum import Enum


class UserStatus(str, Enum):
    NEW = 'new'
    STARTED = 'started'
    LESSON_1_OPENED = 'lesson_1_opened'
    LESSON_1_FOLLOWUP_SENT = 'lesson_1_followup_sent'
    LESSON_2_OPENED = 'lesson_2_opened'
    LESSON_3_OPENED = 'lesson_3_opened'
    OFFER_SENT = 'offer_sent'
    APPLICATION_OPENED = 'application_opened'
    APPLICATION_SUBMITTED = 'application_submitted'
    LOST = 'lost'
    COMPLETED = 'completed'


class TaskStatus(str, Enum):
    PENDING = 'pending'
    ENQUEUED = 'enqueued'
    PROCESSING = 'processing'
    SENT = 'sent'
    CANCELLED = 'cancelled'
    FAILED = 'failed'


class TaskType(str, Enum):
    LESSON_FOLLOWUP = 'lesson_followup'
    APPLICATION_FOLLOWUP = 'application_followup'
    MANUAL_MESSAGE = 'manual_message'


class EventType(str, Enum):
    USER_CREATED = 'user_created'
    STARTED = 'started'
    BUTTON_CLICK = 'button_click'
    LESSON_SENT = 'lesson_sent'
    PLATFORM_CLICK = 'platform_click'
    FOLLOWUP_SENT = 'followup_sent'
    OFFER_SENT = 'offer_sent'
    APPLICATION_OPENED = 'application_opened'
    APPLICATION_SUBMITTED = 'application_submitted'
    STATUS_CHANGED = 'status_changed'
    TASK_CANCELLED = 'task_cancelled'
    MANUAL_ACTION = 'manual_action'
