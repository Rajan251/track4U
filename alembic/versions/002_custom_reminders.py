"""
Alembic migration: 002 — Custom Reminders

Adds:
  - custom_reminders   : user-defined date-based alert configuration
  - reminder_alert_logs: de-duplication log for reminder emails
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "002_custom_reminders"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # custom_reminders table
    op.create_table(
        "custom_reminders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("remind_days_before", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("repeat_interval_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_custom_reminders_org_id"), "custom_reminders", ["org_id"], unique=False
    )
    op.create_index(
        op.f("ix_custom_reminders_user_id"), "custom_reminders", ["user_id"], unique=False
    )

    # reminder_alert_logs table
    op.create_table(
        "reminder_alert_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("custom_reminder_id", sa.String(length=36), nullable=False),
        sa.Column("days_remaining_at_alert", sa.Integer(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["custom_reminder_id"], ["custom_reminders.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reminder_alert_logs_custom_reminder_id"),
        "reminder_alert_logs",
        ["custom_reminder_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("reminder_alert_logs")
    op.drop_table("custom_reminders")
