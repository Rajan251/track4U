import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.task import Task
from app.models.task_alert import TaskAlertLog
from app.services.email import send_email

logger = logging.getLogger(__name__)


def _parse_emails(raw: str | None) -> list[str]:
    """Parse comma-separated email string into a deduplicated list."""
    if not raw or not raw.strip():
        return []
    return [e.strip() for e in raw.split(",") if e.strip()]


def _build_task_alert_html(
    title: str,
    description: str | None,
    due_date: date,
    days_remaining: int,
    project_title: str,
    alert_days_before: int,
) -> tuple[str, str]:
    """Build plain-text and HTML email bodies for a task due-date alert."""
    if days_remaining < 0:
        urgency = "🔴 OVERDUE"
        color = "#ef4444"
    elif days_remaining <= 1:
        urgency = "🔴 DUE TOMORROW"
        color = "#ef4444"
    elif days_remaining <= 3:
        urgency = "🟠 DUE SOON"
        color = "#f97316"
    else:
        urgency = "🔔 UPCOMING"
        color = "#eab308"

    plain = (
        f"{urgency}: Task Due Date Alert\n\n"
        f"Task         : {title}\n"
        f"Project      : {project_title}\n"
        f"Due Date     : {due_date.isoformat()}\n"
        f"Days Left    : {days_remaining} days\n"
        + (f"\nDescription  : {description}\n" if description else "")
        + f"\nThis alert is sent {alert_days_before} days before the due date."
    )

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#0f172a;color:#e2e8f0;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#f97316,#ef4444);padding:24px 32px;">
        <h1 style="margin:0;font-size:20px;color:#fff;">📋 Task Due Date Alert</h1>
        <p style="margin:4px 0 0;font-size:13px;color:#fed7aa;">{urgency}</p>
      </div>
      <div style="padding:28px 32px;">
        <h2 style="margin:0 0 4px;font-size:18px;color:#f1f5f9;">{title}</h2>
        <p style="margin:0 0 20px;font-size:12px;color:#64748b;">Project: {project_title}</p>
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
          <tr><td style="padding:8px 0;color:#94a3b8;width:140px;">📅 Due Date</td><td style="padding:8px 0;font-weight:600;color:{color};">{due_date.isoformat()}</td></tr>
          <tr><td style="padding:8px 0;color:#94a3b8;">⏱ Days Left</td><td style="padding:8px 0;font-weight:700;font-size:18px;color:{color};">{"OVERDUE" if days_remaining < 0 else f"{days_remaining} days"}</td></tr>
          <tr><td style="padding:8px 0;color:#94a3b8;">⚙ Alert Window</td><td style="padding:8px 0;">{alert_days_before} days before due date</td></tr>
        </table>
        {"<div style='margin-top:16px;padding:14px;background:#1e293b;border-radius:8px;'><p style='margin:0;font-size:13px;color:#cbd5e1;'>" + description + "</p></div>" if description else ""}
        <p style="margin-top:20px;font-size:12px;color:#64748b;">
          This alert is sent automatically when a task approaches its due date.
        </p>
      </div>
      <div style="background:#1e293b;padding:12px 32px;text-align:center;font-size:11px;color:#475569;">
        Track4U SaaS · Powered by FastAPI
      </div>
    </div>
    """
    return plain, html


async def run_task_alert_checks(db: AsyncSession) -> int:
    """
    Check all tasks with alert_emails set and a due_date approaching.
    Sends email alerts when (due_date - today).days <= alert_days_before.

    De-duplication: skips if an alert was sent within the last EMAIL_ALERT_DEDUP_HOURS.
    Returns the count of tasks for which alerts were sent.
    """
    dedup_hours = settings.EMAIL_ALERT_DEDUP_HOURS
    dedup_cutoff = datetime.now(timezone.utc) - timedelta(hours=dedup_hours)
    today = date.today()
    sent_count = 0

    # Only tasks that have alert_emails configured and a due_date
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.alert_logs))
        .where(
            Task.alert_emails.isnot(None),
            Task.due_date.isnot(None),
            Task.status.notin_(["done"]),  # skip completed tasks
        )
    )
    tasks = result.scalars().all()

    for task in tasks:
        days_remaining = (task.due_date - today).days

        # Only alert within the configured window
        if days_remaining > task.alert_days_before:
            continue

        # Skip if more than 30 days overdue
        if days_remaining < -30:
            continue

        # Parse extra recipient emails
        extra_emails = _parse_emails(task.alert_emails)
        if not extra_emails:
            continue

        # De-duplication check
        recent = await db.execute(
            select(TaskAlertLog).where(
                TaskAlertLog.task_id == task.id,
                TaskAlertLog.sent_at >= dedup_cutoff,
            )
        )
        if recent.scalar_one_or_none():
            logger.debug(
                f"⏭ Task '{task.title}' alert skipped (sent within last {dedup_hours}h)"
            )
            continue

        # Build email content
        subject = f"[Track4U] Task Due: {task.title} — {days_remaining if days_remaining >= 0 else 'OVERDUE'} days"
        plain, html = _build_task_alert_html(
            title=task.title,
            description=task.description,
            due_date=task.due_date,
            days_remaining=days_remaining,
            project_title=task.project_id,  # will be enriched below if project loaded
            alert_days_before=task.alert_days_before,
        )

        # Merge extra alert_emails with global ALERT_TO_EMAILS (deduplicated)
        all_recipients = list(set(extra_emails) | set(settings.ALERT_TO_EMAILS))
        any_ok = False
        for email_addr in all_recipients:
            ok = await send_email(email_addr, subject, plain, html)
            if ok:
                any_ok = True
                logger.info(f"📧 Task alert sent: '{task.title}' → {email_addr}")

        if any_ok:
            db.add(TaskAlertLog(
                task_id=task.id,
                days_remaining_at_alert=days_remaining,
                sent_at=datetime.now(timezone.utc),
            ))
            await db.commit()
            sent_count += 1

    logger.info(f"📋 Task alert check done: {sent_count} alerts sent out of {len(tasks)} tasks checked.")
    return sent_count
