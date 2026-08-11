from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.services.email import send_email
from app.services.reminder_check import run_reminder_checks
from app.services.task_alert_check import run_task_alert_checks
from app.services.website_check import run_expiry_checks

router = APIRouter(prefix="/internal", tags=["Internal Scheduler"])


def _verify_token(x_internal_token: str) -> None:
    if x_internal_token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal authorization token",
        )


@router.post("/send-test-email")
async def send_test_email(
    x_internal_token: str = Header(..., alias="X-Internal-Token"),
    to_email: Optional[str] = Body(None, embed=True),
) -> Any:
    """
    Send a test email to verify SMTP configuration is working.

    - If `to_email` is provided in the request body, sends to that address.
    - Otherwise sends to the global ALERT_TO_EMAILS list.
    - Protected by X-Internal-Token header.
    """
    _verify_token(x_internal_token)

    subject = "[Track4U] ✅ Test Email — SMTP Configuration Working"
    body = (
        "This is a test email from Track4U.\n\n"
        "If you received this, your SMTP configuration is working correctly.\n\n"
        "Settings verified:\n"
        f"  SMTP Host : {settings.SMTP_HOST}\n"
        f"  SMTP Port : {settings.SMTP_PORT}\n"
        f"  SMTP User : {settings.SMTP_USER or '(not configured — stub mode)'}\n"
        f"  From      : {settings.ALERT_FROM_EMAIL or settings.SMTP_USER or '(not configured)'}\n"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#0f172a;color:#e2e8f0;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#22c55e,#16a34a);padding:24px 32px;">
        <h1 style="margin:0;font-size:20px;color:#fff;">✅ Track4U — Test Email</h1>
        <p style="margin:4px 0 0;font-size:13px;color:#bbf7d0;">SMTP Configuration Check</p>
      </div>
      <div style="padding:28px 32px;">
        <p style="font-size:15px;color:#f1f5f9;margin:0 0 20px;">
          Your SMTP configuration is <strong style="color:#22c55e;">working correctly</strong>! 🎉
        </p>
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
          <tr><td style="padding:8px 0;color:#94a3b8;width:140px;">📬 SMTP Host</td><td style="padding:8px 0;color:#e2e8f0;">{settings.SMTP_HOST}</td></tr>
          <tr><td style="padding:8px 0;color:#94a3b8;">🔌 SMTP Port</td><td style="padding:8px 0;color:#e2e8f0;">{settings.SMTP_PORT}</td></tr>
          <tr><td style="padding:8px 0;color:#94a3b8;">👤 SMTP User</td><td style="padding:8px 0;color:#e2e8f0;">{settings.SMTP_USER or "(stub mode — no credentials)"}</td></tr>
          <tr><td style="padding:8px 0;color:#94a3b8;">📧 From</td><td style="padding:8px 0;color:#e2e8f0;">{settings.ALERT_FROM_EMAIL or settings.SMTP_USER or "(not configured)"}</td></tr>
        </table>
        <p style="margin-top:20px;font-size:12px;color:#64748b;">
          Sent at {__import__("datetime").datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
        </p>
      </div>
      <div style="background:#1e293b;padding:12px 32px;text-align:center;font-size:11px;color:#475569;">
        Track4U SaaS · Powered by FastAPI
      </div>
    </div>
    """

    # Determine recipients
    if to_email and to_email.strip():
        recipients = [to_email.strip()]
    elif settings.ALERT_TO_EMAILS:
        recipients = list(settings.ALERT_TO_EMAILS)
    else:
        # No recipient configured at all — stub will log it
        recipients = ["test@example.com"]

    results = {}
    for addr in recipients:
        ok = await send_email(addr, subject, body, html)
        results[addr] = "sent" if ok else "failed"

    all_ok = all(v == "sent" for v in results.values())
    return {
        "status": "success" if all_ok else "partial_failure",
        "message": "Test email(s) dispatched." if all_ok else "Some emails failed — check SMTP config.",
        "smtp_configured": bool(settings.SMTP_USER and settings.SMTP_USER.strip()),
        "recipients": results,
    }


@router.post("/run-expiry-checks")
async def trigger_expiry_checks(
    x_internal_token: str = Header(..., alias="X-Internal-Token"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Manually trigger domain & SSL expiry checks for all active tracked websites.
    Protected by X-Internal-Token header.
    """
    _verify_token(x_internal_token)
    checked_count = await run_expiry_checks(db)
    return {
        "status": "success",
        "message": f"Expiry checks completed for {checked_count} active websites.",
        "websites_checked": checked_count,
    }


@router.post("/run-reminder-checks")
async def trigger_reminder_checks(
    x_internal_token: str = Header(..., alias="X-Internal-Token"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Manually trigger reminder alerts for all active custom reminders.
    Protected by X-Internal-Token header.
    """
    _verify_token(x_internal_token)
    sent_count = await run_reminder_checks(db)
    return {
        "status": "success",
        "message": f"Reminder checks completed. {sent_count} alert emails sent.",
        "alerts_sent": sent_count,
    }


@router.post("/run-task-alerts")
async def trigger_task_alerts(
    x_internal_token: str = Header(..., alias="X-Internal-Token"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Manually trigger task due-date alert emails for all tasks with alert_emails configured.
    Protected by X-Internal-Token header.
    """
    _verify_token(x_internal_token)
    sent_count = await run_task_alert_checks(db)
    return {
        "status": "success",
        "message": f"Task alert checks completed. {sent_count} alert emails sent.",
        "alerts_sent": sent_count,
    }


@router.post("/run-all-checks")
async def trigger_all_checks(
    x_internal_token: str = Header(..., alias="X-Internal-Token"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Manually trigger ALL checks in one call:
    - Domain/SSL expiry checks
    - Custom reminder checks
    - Task due-date alert checks

    Equivalent to what the scheduler runs 2× per day.
    """
    _verify_token(x_internal_token)
    websites_checked = await run_expiry_checks(db)
    alerts_sent = await run_reminder_checks(db)
    task_alerts_sent = await run_task_alert_checks(db)
    return {
        "status": "success",
        "message": "All checks completed.",
        "websites_checked": websites_checked,
        "reminder_alerts_sent": alerts_sent,
        "task_alerts_sent": task_alerts_sent,
    }
