"""initial

Revision ID: 20260422_000001
Revises: None
Create Date: 2026-04-22 17:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = '20260422_000001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=64), nullable=False),
        sa.Column('current_stage', sa.String(length=128), nullable=False),
        sa.Column('current_lesson', sa.Integer(), nullable=False),
        sa.Column('lesson_2_reached', sa.Boolean(), nullable=False),
        sa.Column('lesson_3_reached', sa.Boolean(), nullable=False),
        sa.Column('application_opened', sa.Boolean(), nullable=False),
        sa.Column('application_submitted', sa.Boolean(), nullable=False),
        sa.Column('unsubscribed', sa.Boolean(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('extra_data', sa.JSON(), nullable=False),
        sa.Column('last_interaction_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id'),
    )
    op.create_index(op.f('ix_users_current_stage'), 'users', ['current_stage'], unique=False)
    op.create_index(op.f('ix_users_source'), 'users', ['source'], unique=False)
    op.create_index(op.f('ix_users_status'), 'users', ['status'], unique=False)
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=False)

    op.create_table(
        'user_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('stage', sa.String(length=128), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_events_event_type'), 'user_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_user_events_stage'), 'user_events', ['stage'], unique=False)
    op.create_index(op.f('ix_user_events_user_id'), 'user_events', ['user_id'], unique=False)

    op.create_table(
        'scheduled_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('task_type', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('dedup_key', sa.String(length=255), nullable=False),
        sa.Column('run_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('redis_job_id', sa.String(length=255), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retries', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedup_key', name='uq_scheduled_tasks_dedup_key'),
    )
    op.create_index(op.f('ix_scheduled_tasks_redis_job_id'), 'scheduled_tasks', ['redis_job_id'], unique=False)
    op.create_index(op.f('ix_scheduled_tasks_run_at'), 'scheduled_tasks', ['run_at'], unique=False)
    op.create_index(op.f('ix_scheduled_tasks_status'), 'scheduled_tasks', ['status'], unique=False)
    op.create_index(op.f('ix_scheduled_tasks_task_type'), 'scheduled_tasks', ['task_type'], unique=False)
    op.create_index(op.f('ix_scheduled_tasks_user_id'), 'scheduled_tasks', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_scheduled_tasks_user_id'), table_name='scheduled_tasks')
    op.drop_index(op.f('ix_scheduled_tasks_task_type'), table_name='scheduled_tasks')
    op.drop_index(op.f('ix_scheduled_tasks_status'), table_name='scheduled_tasks')
    op.drop_index(op.f('ix_scheduled_tasks_run_at'), table_name='scheduled_tasks')
    op.drop_index(op.f('ix_scheduled_tasks_redis_job_id'), table_name='scheduled_tasks')
    op.drop_table('scheduled_tasks')

    op.drop_index(op.f('ix_user_events_user_id'), table_name='user_events')
    op.drop_index(op.f('ix_user_events_stage'), table_name='user_events')
    op.drop_index(op.f('ix_user_events_event_type'), table_name='user_events')
    op.drop_table('user_events')

    op.drop_index(op.f('ix_users_telegram_id'), table_name='users')
    op.drop_index(op.f('ix_users_status'), table_name='users')
    op.drop_index(op.f('ix_users_source'), table_name='users')
    op.drop_index(op.f('ix_users_current_stage'), table_name='users')
    op.drop_table('users')
