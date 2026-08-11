"""
APScheduler background job scheduler for Track4U.

Runs two cron jobs per day (configurable via .env):
  - Default run 1: 02:30 UTC = 08:00 AM IST
  - Default run 2: 14:30 UTC = 08:00 PM IST

Each run:
  1. Checks all tracked websites for domain/SSL expiry → sends alert emails
  2. Checks all custom reminders → sends reminder alert emails
  3. Checks all tasks with alert_emails for approaching due dates → sends task alerts
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.db.session import async_session_factory
from app.services.reminder_check import run_reminder_checks
from app.services.task_alert_check import run_task_alert_checks
from app.services.website_check import run_expiry_checks

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _scheduled_job() -> None:
    """Combined scheduled job: expiry checks + reminder checks + task due-date alerts."""
    logger.info("⏰ Scheduled job started: running all checks...")
    async with async_session_factory() as db:
        try:
            websites_checked = await run_expiry_checks(db)
            reminders_checked = await run_reminder_checks(db)
            task_alerts_sent = await run_task_alert_checks(db)
            logger.info(
                f"✅ Scheduled job done — "
                f"{websites_checked} websites checked, "
                f"{reminders_checked} reminder alerts sent, "
                f"{task_alerts_sent} task alerts sent."
            )
        except Exception as e:
            logger.error(f"❌ Scheduled job error: {e}", exc_info=True)


def start_scheduler() -> AsyncIOScheduler:
    """
    Creates and starts the AsyncIOScheduler with two daily cron triggers.
    Returns the scheduler instance so it can be shut down on app teardown.
    """
    global _scheduler

    scheduler = AsyncIOScheduler(timezone="UTC")

    # First daily run (default: 02:30 UTC = 8:00 AM IST)
    scheduler.add_job(
        _scheduled_job,
        trigger=CronTrigger(
            hour=settings.SCHEDULER_HOUR_1,
            minute=settings.SCHEDULER_MINUTE_1,
            timezone="UTC",
        ),
        id="expiry_check_run1",
        name="Morning Expiry & Reminder Check (8AM IST)",
        replace_existing=True,
        misfire_grace_time=300,  # fire up to 5 min late if app was down
    )

    # Second daily run (default: 14:30 UTC = 8:00 PM IST)
    scheduler.add_job(
        _scheduled_job,
        trigger=CronTrigger(
            hour=settings.SCHEDULER_HOUR_2,
            minute=settings.SCHEDULER_MINUTE_2,
            timezone="UTC",
        ),
        id="expiry_check_run2",
        name="Evening Expiry & Reminder Check (8PM IST)",
        replace_existing=True,
        misfire_grace_time=300,
    )

    scheduler.start()
    _scheduler = scheduler

    logger.info(
        f"🕐 Scheduler started with 2 daily jobs:\n"
        f"   Run 1: {settings.SCHEDULER_HOUR_1:02d}:{settings.SCHEDULER_MINUTE_1:02d} UTC\n"
        f"   Run 2: {settings.SCHEDULER_HOUR_2:02d}:{settings.SCHEDULER_MINUTE_2:02d} UTC"
    )
    return scheduler


def stop_scheduler() -> None:
    """Gracefully shuts down the scheduler on app teardown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("⏹ Scheduler stopped.")
    _scheduler = None
