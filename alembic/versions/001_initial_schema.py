"""Initial Schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-07-29 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('notify_on_expiry', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('subscription_status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('plan_type', sa.String(length=50), nullable=False, server_default='free'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    # Org Members
    op.create_table(
        'org_members',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='member'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id', 'user_id', name='uq_org_user')
    )

    # Projects
    op.create_table(
        'projects',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_org_id'), 'projects', ['org_id'], unique=False)

    # Labels
    op.create_table(
        'labels',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('color', sa.String(length=50), nullable=False, server_default='#3B82F6'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_labels_org_id'), 'labels', ['org_id'], unique=False)

    # Tasks
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='todo'),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='medium'),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('assignee_id', sa.String(length=36), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_org_id'), 'tasks', ['org_id'], unique=False)
    op.create_index(op.f('ix_tasks_project_id'), 'tasks', ['project_id'], unique=False)

    # Task Labels
    op.create_table(
        'task_labels',
        sa.Column('task_id', sa.String(length=36), nullable=False),
        sa.Column('label_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['label_id'], ['labels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('task_id', 'label_id')
    )

    # Comments
    op.create_table(
        'comments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('task_id', sa.String(length=36), nullable=False),
        sa.Column('author_id', sa.String(length=36), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_comments_task_id'), 'comments', ['task_id'], unique=False)

    # Activity Logs
    op.create_table(
        'activity_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('task_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activity_logs_task_id'), 'activity_logs', ['task_id'], unique=False)

    # Tracked Websites
    op.create_table(
        'tracked_websites',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.String(length=36), nullable=False),
        sa.Column('added_by', sa.String(length=36), nullable=False),
        sa.Column('url', sa.String(length=512), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('domain_expiry_date', sa.Date(), nullable=True),
        sa.Column('ssl_expiry_date', sa.Date(), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_check_status', sa.String(length=50), nullable=True),
        sa.Column('last_check_error', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tracked_websites_org_id'), 'tracked_websites', ['org_id'], unique=False)

    # Expiry Alert Logs
    op.create_table(
        'expiry_alert_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tracked_website_id', sa.String(length=36), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('days_remaining_at_alert', sa.Integer(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tracked_website_id'], ['tracked_websites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expiry_alert_logs_tracked_website_id'), 'expiry_alert_logs', ['tracked_website_id'], unique=False)


def downgrade() -> None:
    op.drop_table('expiry_alert_logs')
    op.drop_table('tracked_websites')
    op.drop_table('activity_logs')
    op.drop_table('comments')
    op.drop_table('task_labels')
    op.drop_table('tasks')
    op.drop_table('labels')
    op.drop_table('projects')
    op.drop_table('org_members')
    op.drop_table('organizations')
    op.drop_table('users')
