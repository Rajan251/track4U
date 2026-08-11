import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(to_email: str, subject: str, body: str, html_body: str = "") -> bool:
    """
    Send an email to the given address.

    If SMTP_USER is not configured, logs the email to stdout instead (stub mode).
    Supports both plain-text and HTML content.
    """
    # Stub mode: SMTP credentials not configured
    if not settings.SMTP_USER or not settings.SMTP_USER.strip():
        logger.info(
            f"[STUB EMAIL — configure SMTP_USER in .env to send real mail]\n"
            f"  To     : {to_email}\n"
            f"  Subject: {subject}\n"
            f"  Body   :\n{body}"
        )
        return True

    msg = EmailMessage()
    msg["From"] = settings.ALERT_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)  # plain-text fallback

    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=(settings.SMTP_PORT == 587),
            use_tls=(settings.SMTP_PORT == 465),
            timeout=15,
        )
        logger.info(f"✅ Email sent to {to_email} | Subject: {subject}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to_email}: {e}")
        return False
