from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.reminder import CustomReminder, ReminderAlertLog
from app.models.user import User
from app.services.email import send_email

import logging

logger = logging.getLogger(__name__)


def _build_reminder_html(
    title: str,
    description: str,
    target_date: date,
    days_remaining: int,
    remind_days_before: int,
) -> tuple[str, str]:
    """Build plain-text and HTML email bodies for a custom reminder alert."""
    urgency = "🔴 URGENT" if days_remaining <= 3 else "🟡 SOON" if days_remaining <= 7 else "🔔 REMINDER"

    plain = (
        f"{urgency}: {title}\n\n"
        f"Target Date : {target_date.isoformat()}\n"
        f"Days Left   : {days_remaining} days\n"
        + (f"\nNotes: {description}\n" if description else "")
        + f"\nThis reminder was set to alert you {remind_days_before} days before the date."
    )

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#0f172a;color:#e2e8f0;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#0ea5e9,#6366f1);padding:24px 32px;">
        <h1 style="margin:0;font-size:20px;color:#fff;">🔔 Track4U Reminder</h1>
        <p style="margin:4px 0 0;font-size:13px;color:#bae6fd;">{urgency}</p>
      </div>
      <div style="padding:28px 32px;">
        <h2 style="margin:0 0 16px;font-size:18px;color:#f1f5f9;">{title}</h2>
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
          <tr><td style="padding:8px 0;color:#94a3b8;width:140px;">📅 Target Date</td><td style="padding:8px 0;font-weight:600;color:#f87171;">{target_date.isoformat()}</td></tr>
          <tr><td style="padding:8px 0;color:#94a3b8;">⏱ Days Left</td><td style="padding:8px 0;font-weight:700;font-size:18px;color:#fbbf24;">{days_remaining} days</td></tr>
          <tr><td style="padding:8px 0;color:#94a3b8;">⚙ Alert Window</td><td style="padding:8px 0;">from {remind_days_before} days before</td></tr>
        </table>
        {"<div style='margin-top:16px;padding:14px;background:#1e293b;border-radius:8px;'><p style='margin:0;font-size:13px;color:#cbd5e1;'>" + description + "</p></div>" if description else ""}
        <p style="margin-top:20px;font-size:12px;color:#64748b;">
          This alert is sent twice daily (8:00 AM &amp; 8:00 PM IST) during the reminder window.
        </p>
      </div>
      <div style="background:#1e293b;padding:12px 32px;text-align:center;font-size:11px;color:#475569;">
        Track4U SaaS · Powered by FastAPI
      </div>
    </div>
    """
    return plain, html


async def run_reminder_checks(db: AsyncSession) -> int:
    """
    Check all active custom reminders and send email alerts when
    (target_date - today).days <= remind_days_before.

    De-duplication: skips if an alert was sent within the last EMAIL_ALERT_DEDUP_HOURS.
    """
    dedup_hours = settings.EMAIL_ALERT_DEDUP_HOURS
    dedup_cutoff = datetime.now(timezone.utc) - timedelta(hours=dedup_hours)
    today = date.today()
    sent_count = 0

    result = await db.execute(
        select(CustomReminder).where(CustomReminder.is_active == True)
    )
    reminders = result.scalars().all()

    for reminder in reminders:
        days_remaining = (reminder.target_date - today).days

        # Only alert within the configured window
        if days_remaining > reminder.remind_days_before:
            continue

        # Skip if it's very far past (more than 30 days overdue), unless repeating
        if days_remaining < -30 and not reminder.repeat_interval_days:
            continue

        # Fetch the owner to get their email
        user_result = await db.execute(
            select(User).where(User.id == reminder.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            continue

        # De-duplication check
        recent = await db.execute(
            select(ReminderAlertLog).where(
                ReminderAlertLog.custom_reminder_id == reminder.id,
                ReminderAlertLog.sent_at >= dedup_cutoff,
            )
        )
        if recent.scalar_one_or_none():
            logger.debug(
                f"⏭ Reminder '{reminder.title}' skipped (sent within last {dedup_hours}h)"
            )
            continue

        # Build email content once
        subject = f"[Track4U] Reminder: {reminder.title} — {days_remaining} days left"
        plain, html = _build_reminder_html(
            reminder.title,
            reminder.description or "",
            reminder.target_date,
            days_remaining,
            reminder.remind_days_before,
        )

        # Merge owner email + per-reminder alert_emails + global ALERT_TO_EMAILS (deduplicated)
        extra = [e.strip() for e in (reminder.alert_emails or "").split(",") if e.strip()]
        all_recipients = list({user.email} | set(extra) | set(settings.ALERT_TO_EMAILS))
        any_ok = False
        for email_addr in all_recipients:
            ok = await send_email(email_addr, subject, plain, html)
            if ok:
                any_ok = True
                logger.info(f"📧 Reminder alert sent: '{reminder.title}' → {email_addr}")

        if any_ok:
            db.add(ReminderAlertLog(
                custom_reminder_id=reminder.id,
                days_remaining_at_alert=days_remaining,
                sent_at=datetime.now(timezone.utc),
            ))
            await db.commit()
            sent_count += 1

    logger.info(f"🔔 Reminder check done: {sent_count} alerts sent out of {len(reminders)} reminders.")
    return sent_count

