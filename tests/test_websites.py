from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.website import ExpiryAlertLog


@pytest.mark.asyncio
async def test_tracked_website_crud_and_mocked_check(client: AsyncClient):
    # Signup
    res = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "webuser@example.com",
            "password": "Password123!",
            "full_name": "Web Tracker User",
            "org_name": "Web Org",
        },
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Mock SSL and WHOIS check functions
    with (
        patch("app.services.website_check.check_ssl_expiry_sync") as mock_ssl,
        patch("app.services.website_check.check_domain_expiry_sync") as mock_whois,
    ):

        mock_ssl.return_value = (date.today() + timedelta(days=20), None)
        mock_whois.return_value = (date.today() + timedelta(days=15), None)

        # Add Website
        add_resp = await client.post(
            "/api/v1/websites",
            json={
                "url": "https://myservice.org",
                "label": "Production Gateway",
            },
            headers=headers,
        )

        assert add_resp.status_code == 201
        data = add_resp.json()
        assert data["label"] == "Production Gateway"
        assert data["domain_days_remaining"] == 15
        assert data["ssl_days_remaining"] == 20
        assert data["last_check_status"] == "ok"
        website_id = data["id"]

        # Manual Check Now
        mock_ssl.return_value = (date.today() + timedelta(days=19), None)
        check_now_resp = await client.post(
            f"/api/v1/websites/{website_id}/check-now", headers=headers
        )
        assert check_now_resp.status_code == 200
        assert check_now_resp.json()["ssl_days_remaining"] == 19


@pytest.mark.asyncio
async def test_expiry_alert_deduplication_logic(client: AsyncClient, db_session):
    # Setup user
    res = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "alertuser@example.com",
            "password": "Password123!",
            "full_name": "Alert User",
            "org_name": "Alert Org",
        },
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Mock SSL, WHOIS, and Email
    with (
        patch("app.services.website_check.check_ssl_expiry_sync") as mock_ssl,
        patch("app.services.website_check.check_domain_expiry_sync") as mock_whois,
        patch("app.services.website_check.send_email", new_callable=AsyncMock) as mock_send_email,
    ):

        # Expiry date is 10 days away (within 30 days threshold)
        mock_ssl.return_value = (date.today() + timedelta(days=10), None)
        mock_whois.return_value = (date.today() + timedelta(days=10), None)

        # Add website
        add_resp = await client.post(
            "/api/v1/websites",
            json={
                "url": "https://expiring-soon.com",
                "label": "Expiring Site",
            },
            headers=headers,
        )
        website_id = add_resp.json()["id"]

        # Run 1st internal check -> Should send emails & log alerts
        internal_headers = {"X-Internal-Token": "internal-secret-token-change-in-production"}
        trigger1 = await client.post("/api/v1/internal/run-expiry-checks", headers=internal_headers)
        assert trigger1.status_code == 200
        assert trigger1.json()["websites_checked"] >= 1

        first_call_count = mock_send_email.call_count
        assert first_call_count > 0, "Email alert should be dispatched on 1st run"

        # Check ExpiryAlertLog records in DB
        logs_res = await db_session.execute(
            select(ExpiryAlertLog).where(ExpiryAlertLog.tracked_website_id == website_id)
        )
        logs = logs_res.scalars().all()
        assert len(logs) == 2  # 1 for domain, 1 for ssl

        # Reset call count
        mock_send_email.reset_mock()

        # Run 2nd internal check immediately (same calendar week) -> Should NOT send duplicate email!
        trigger2 = await client.post("/api/v1/internal/run-expiry-checks", headers=internal_headers)
        assert trigger2.status_code == 200
        assert (
            mock_send_email.call_count == 0
        ), "De-duplication logic failed: duplicate alert sent within 7 days!"
