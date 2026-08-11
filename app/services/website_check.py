import asyncio
import logging
import socket
import ssl
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple
from urllib.parse import urlparse

import whois
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.org import OrgMember
from app.models.user import User
from app.models.website import ExpiryAlertLog, TrackedWebsite
from app.services.email import send_email

logger = logging.getLogger(__name__)


def check_ssl_expiry_sync(
    hostname: str, port: int = 443, timeout: float = 10.0
) -> Tuple[Optional[date], Optional[str]]:
    """
    Connect to host via SSL on port 443, extract certificate's notAfter field and parse to date.
    Returns (ssl_expiry_date, error_message).
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                if not cert or "notAfter" not in cert:
                    return None, "No valid SSL certificate found or missing notAfter field"

                not_after_str = cert["notAfter"]
                # Standard SSL date format: 'May 20 23:59:59 2025 GMT'
                ssl_date = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").date()
                return ssl_date, None
    except Exception as e:
        logger.warning(f"SSL check failed for {hostname}: {e}")
        return None, f"SSL check failed: {str(e)}"


def check_domain_expiry_sync(domain: str) -> Tuple[Optional[date], Optional[str]]:
    """
    Look up WHOIS record for the domain to extract expiration date.
    Returns (domain_expiry_date, error_message).
    """
    try:
        w = whois.whois(domain)
        exp_date = w.expiration_date
        if isinstance(exp_date, list):
            exp_date = exp_date[0]

        if isinstance(exp_date, datetime):
            return exp_date.date(), None
        elif isinstance(exp_date, date):
            return exp_date, None
        else:
            return None, "WHOIS lookup returned no valid expiration date"
    except Exception as e:
        logger.warning(f"WHOIS check failed for {domain}: {e}")
        return None, f"WHOIS lookup failed: {str(e)}"


def extract_host_and_domain(url: str) -> Tuple[str, str]:
    parsed = urlparse(url)
    hostname = parsed.netloc or parsed.path
    if ":" in hostname:
        hostname = hostname.split(":")[0]

    # Strip subdomains for WHOIS if needed (basic domain extraction)
    parts = hostname.split(".")
    if len(parts) >= 2:
        domain = ".".join(parts[-2:])
    else:
        domain = hostname
    return hostname, domain


async def check_single_website(db: AsyncSession, website: TrackedWebsite) -> TrackedWebsite:
    """
    Executes SSL certificate check and WHOIS domain check for a single TrackedWebsite record.
    """
    hostname, domain = extract_host_and_domain(website.url)

    # Run sync checks in threadpool to avoid blocking async loop
    loop = asyncio.get_running_loop()
    ssl_date, ssl_err = await loop.run_in_executor(None, check_ssl_expiry_sync, hostname)
    domain_date, domain_err = await loop.run_in_executor(None, check_domain_expiry_sync, domain)

    website.ssl_expiry_date = ssl_date or website.ssl_expiry_date
    website.domain_expiry_date = domain_date or website.domain_expiry_date
    website.last_checked_at = datetime.now(timezone.utc)

    errors = []
    if ssl_err:
        errors.append(ssl_err)
    if domain_err:
        errors.append(domain_err)

    if errors and not (ssl_date or domain_date):
        website.last_check_status = "error"
        website.last_check_error = " | ".join(errors)
    else:
        website.last_check_status = "ok"
        website.last_check_error = " | ".join(errors) if errors else None

    await db.commit()
    await db.refresh(website)
    return website


def _build_alert_html(
    site_label: str,
    site_url: str,
    alert_type: str,
    expiry_date: date,
    days_remaining: int,
    threshold: int,
) -> Tuple[str, str]:
    """Build plain-text and HTML bodies for an expiry alert email."""
    type_label = "Domain Registration" if alert_type == "domain" else "SSL Certificate"
    urgency = "🔴 CRITICAL" if days_remaining <= 7 else "🟡 WARNING" if days_remaining <= 14 else "🟢 NOTICE"
    action = "renew your domain registration" if alert_type == "domain" else "renew your SSL certificate"

    plain = (
        f"{urgency} — {type_label} Expiry Alert\n\n"
        f"Site   : {site_label} ({site_url})\n"
        f"Type   : {type_label}\n"
        f"Expires: {expiry_date.isoformat()}\n"
        f"Days   : {days_remaining} days remaining\n\n"
        f"Please {action} soon to avoid service disruption.\n"
        f"This alert is sent twice daily while expiry is within {threshold} days."
    )

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#0f172a;color:#e2e8f0;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:24px 32px;">
        <h1 style="margin:0;font-size:20px;color:#fff;">⚡ Track4U Alert</h1>
        <p style="margin:4px 0 0;font-size:13px;color:#c7d2fe;">{urgency} — {type_label} Expiry</p>
      </div>
      <div style="padding:28px 32px;">
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
          <tr><td style="padding:8px 0;color:#94a3b8;width:120px;">🌐 Site</td><td style="padding:8px 0;font-weight:600;">{site_label}</td></tr>
          <tr><td style="padding:8px 0;color:#94a3b8;">🔗 URL</td><td style="padding:8px 0;color:#818cf8;">{site_url}</td></tr>
          <tr><td style="padding:8px 0;color:#94a3b8;">📋 Type</td><td style="padding:8px 0;">{type_label}</td></tr>
          <tr><td style="padding:8px 0;color:#94a3b8;">📅 Expires</td><td style="padding:8px 0;color:#f87171;font-weight:600;">{expiry_date.isoformat()}</td></tr>
          <tr><td style="padding:8px 0;color:#94a3b8;">⏱ Remaining</td><td style="padding:8px 0;color:#fbbf24;font-weight:700;font-size:18px;">{days_remaining} days</td></tr>
        </table>
        <div style="margin-top:20px;padding:16px;background:#1e293b;border-radius:8px;border-left:4px solid #f87171;">
          <p style="margin:0;font-size:13px;">⚠️ Please <strong>{action}</strong> to prevent service disruption.</p>
        </div>
        <p style="margin-top:16px;font-size:12px;color:#64748b;">
          This alert is sent twice daily (8:00 AM &amp; 8:00 PM IST) while expiry is within {threshold} days.<br>
          Alerts automatically stop once the domain/SSL is renewed.
        </p>
      </div>
      <div style="background:#1e293b;padding:12px 32px;text-align:center;font-size:11px;color:#475569;">
        Track4U SaaS · Powered by FastAPI
      </div>
    </div>
    """
    return plain, html


async def run_expiry_checks(db: AsyncSession) -> int:
    """
    Iterates over all active tracked websites across all organizations,
    performs SSL & WHOIS checks, and sends de-duplicated email alerts.

    DE-DUPLICATION:
    - An alert is sent ONLY if no ExpiryAlertLog for the same site and alert_type
      was created within the last EMAIL_ALERT_DEDUP_HOURS hours (default 11h,
      allowing 2×/day sends at 8AM and 8PM IST).

    AUTO-STOP:
    - If expiry is BEYOND the threshold (renewed), no email is sent and stale
      alert logs older than 30 days are cleaned up.
    """
    from app.core.config import settings as cfg

    result = await db.execute(select(TrackedWebsite).where(TrackedWebsite.is_active == True))
    websites = result.scalars().all()

    checked_count = 0
    today = date.today()
    threshold = cfg.ALERT_THRESHOLD_DAYS
    dedup_hours = cfg.EMAIL_ALERT_DEDUP_HOURS

    for website in websites:
        await check_single_website(db, website)
        checked_count += 1

        # Get users in this org who have notify_on_expiry = True
        users_result = await db.execute(
            select(User)
            .join(OrgMember, OrgMember.user_id == User.id)
            .where(
                OrgMember.org_id == website.org_id,
                User.notify_on_expiry == True,
            )
        )
        recipients = users_result.scalars().all()
        # Merge per-user emails (notify_on_expiry=True) with global ALERT_TO_EMAILS
        user_emails = {u.email for u in recipients}
        all_alert_emails = list(user_emails | set(cfg.ALERT_TO_EMAILS))
        if not all_alert_emails:
            continue

        dedup_cutoff = datetime.now(timezone.utc) - timedelta(hours=dedup_hours)

        # --- 1. Domain Expiry Alert ---
        if website.domain_expiry_date:
            domain_days = (website.domain_expiry_date - today).days

            if domain_days > threshold:
                # AUTO-STOP: domain renewed — clean up old alert logs
                logger.info(
                    f"✅ Domain renewed for {website.url}: {domain_days} days remaining "
                    f"(threshold={threshold}). Clearing stale alert logs."
                )
                stale_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                await db.execute(
                    delete(ExpiryAlertLog).where(
                        ExpiryAlertLog.tracked_website_id == website.id,
                        ExpiryAlertLog.alert_type == "domain",
                        ExpiryAlertLog.sent_at < stale_cutoff,
                    )
                )
                await db.commit()
            else:
                # Check de-duplication window (11h default → allows 2×/day)
                recent_alert = await db.execute(
                    select(ExpiryAlertLog).where(
                        ExpiryAlertLog.tracked_website_id == website.id,
                        ExpiryAlertLog.alert_type == "domain",
                        ExpiryAlertLog.sent_at >= dedup_cutoff,
                    )
                )
                if not recent_alert.scalar_one_or_none():
                    site_label = website.label or website.url
                    subject = f"[Track4U] Domain Expiry: {site_label} — {domain_days} days left"
                    plain, html = _build_alert_html(
                        site_label, website.url, "domain",
                        website.domain_expiry_date, domain_days, threshold
                    )
                    for addr in all_alert_emails:
                        await send_email(addr, subject, plain, html)
                        logger.info(f"📧 Domain alert → {addr} ({domain_days}d left)")

                    db.add(ExpiryAlertLog(
                        tracked_website_id=website.id,
                        alert_type="domain",
                        days_remaining_at_alert=domain_days,
                        sent_at=datetime.now(timezone.utc),
                    ))
                    await db.commit()
                else:
                    logger.debug(
                        f"⏭ Domain alert for {website.url} skipped "
                        f"(sent within last {dedup_hours}h)"
                    )

        # --- 2. SSL Expiry Alert ---
        if website.ssl_expiry_date:
            ssl_days = (website.ssl_expiry_date - today).days

            if ssl_days > threshold:
                # AUTO-STOP: SSL renewed — clean up old alert logs
                logger.info(
                    f"✅ SSL renewed for {website.url}: {ssl_days} days remaining "
                    f"(threshold={threshold}). Clearing stale alert logs."
                )
                stale_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                await db.execute(
                    delete(ExpiryAlertLog).where(
                        ExpiryAlertLog.tracked_website_id == website.id,
                        ExpiryAlertLog.alert_type == "ssl",
                        ExpiryAlertLog.sent_at < stale_cutoff,
                    )
                )
                await db.commit()
            else:
                recent_alert = await db.execute(
                    select(ExpiryAlertLog).where(
                        ExpiryAlertLog.tracked_website_id == website.id,
                        ExpiryAlertLog.alert_type == "ssl",
                        ExpiryAlertLog.sent_at >= dedup_cutoff,
                    )
                )
                if not recent_alert.scalar_one_or_none():
                    site_label = website.label or website.url
                    subject = f"[Track4U] SSL Expiry: {site_label} — {ssl_days} days left"
                    plain, html = _build_alert_html(
                        site_label, website.url, "ssl",
                        website.ssl_expiry_date, ssl_days, threshold
                    )
                    for addr in all_alert_emails:
                        await send_email(addr, subject, plain, html)
                        logger.info(f"📧 SSL alert → {addr} ({ssl_days}d left)")

                    db.add(ExpiryAlertLog(
                        tracked_website_id=website.id,
                        alert_type="ssl",
                        days_remaining_at_alert=ssl_days,
                        sent_at=datetime.now(timezone.utc),
                    ))
                    await db.commit()
                else:
                    logger.debug(
                        f"⏭ SSL alert for {website.url} skipped "
                        f"(sent within last {dedup_hours}h)"
                    )

    logger.info(f"🔍 Expiry check completed: {checked_count} websites processed.")
    return checked_count
