"""
Alembic migration: 003 — Alert Emails & Task Alerts

Adds:
  - alert_emails column to custom_reminders (per-reminder extra recipients)
  - alert_emails column to tasks (per-task alert recipients)
  - alert_days_before column to tasks (days before due_date to start alerting)
  - task_alert_logs table (de-duplication for task due-date alert emails)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "003_alert_emails"
down_revision: Union[str, None] = "002_custom_reminders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add alert_emails to custom_reminders
    with op.batch_alter_table("custom_reminders") as batch_op:
        batch_op.add_column(
            sa.Column("alert_emails", sa.Text(), nullable=True)
        )

    # Add alert_emails and alert_days_before to tasks
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(
            sa.Column("alert_emails", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("alert_days_before", sa.Integer(), nullable=False, server_default="3")
        )

    # Create task_alert_logs table for dedup
    op.create_table(
        "task_alert_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("days_remaining_at_alert", sa.Integer(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_task_alert_logs_task_id"),
        "task_alert_logs",
        ["task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_task_alert_logs_task_id"), table_name="task_alert_logs")
    op.drop_table("task_alert_logs")

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("alert_days_before")
        batch_op.drop_column("alert_emails")

    with op.batch_alter_table("custom_reminders") as batch_op:
        batch_op.drop_column("alert_emails")
