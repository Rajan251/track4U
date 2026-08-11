import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_signup_and_login(client: AsyncClient):
    # 1. Signup
    signup_payload = {
        "email": "user1@example.com",
        "password": "Password123!",
        "full_name": "Test User One",
        "org_name": "Org Alpha",
    }
    response = await client.post("/api/v1/auth/signup", json=signup_payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    token = data["access_token"]

    # 2. Get Me
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "user1@example.com"
    assert me_data["full_name"] == "Test User One"

    # 3. Login
    login_payload = {
        "email": "user1@example.com",
        "password": "Password123!",
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()
