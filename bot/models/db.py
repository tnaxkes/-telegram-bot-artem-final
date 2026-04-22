from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.enums import TaskStatus, TaskType, UserStatus
from config.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(64), default=UserStatus.NEW.value, index=True)
    current_stage: Mapped[str] = mapped_column(String(128), default='start', index=True)
    current_lesson: Mapped[int] = mapped_column(Integer, default=0)
    lesson_2_reached: Mapped[bool] = mapped_column(Boolean, default=False)
    lesson_3_reached: Mapped[bool] = mapped_column(Boolean, default=False)
    application_opened: Mapped[bool] = mapped_column(Boolean, default=False)
    application_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    unsubscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    events: Mapped[list['UserEvent']] = relationship(back_populates='user', cascade='all, delete-orphan')
    tasks: Mapped[list['ScheduledTask']] = relationship(back_populates='user', cascade='all, delete-orphan')


class UserEvent(Base):
    __tablename__ = 'user_events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    stage: Mapped[str | None] = mapped_column(String(128), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped['User'] = relationship(back_populates='events')


class ScheduledTask(Base, TimestampMixin):
    __tablename__ = 'scheduled_tasks'
    __table_args__ = (UniqueConstraint('dedup_key', name='uq_scheduled_tasks_dedup_key'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    task_type: Mapped[str] = mapped_column(String(64), default=TaskType.LESSON_FOLLOWUP.value, index=True)
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.PENDING.value, index=True)
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    redis_job_id: Mapped[str | None] = mapped_column(String(255), index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    retries: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped['User'] = relationship(back_populates='tasks')
