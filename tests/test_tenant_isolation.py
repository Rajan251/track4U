import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tenant_isolation(client: AsyncClient):
    # Create User A & Org A
    res_a = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "userA@example.com",
            "password": "Password123!",
            "full_name": "User A",
            "org_name": "Org A",
        },
    )
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Create User B & Org B
    res_b = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "userB@example.com",
            "password": "Password123!",
            "full_name": "User B",
            "org_name": "Org B",
        },
    )
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a Project in Org A
    proj_a_resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Secret Org A Project",
            "description": "Org A Confidential",
        },
        headers=headers_a,
    )
    assert proj_a_resp.status_code == 201
    proj_a_id = proj_a_resp.json()["id"]

    # User B lists projects -> Should NOT see Org A's project
    proj_list_b = await client.get("/api/v1/projects", headers=headers_b)
    assert proj_list_b.status_code == 200
    b_project_ids = [p["id"] for p in proj_list_b.json()]
    assert proj_a_id not in b_project_ids

    # User B tries to directly access Org A's project -> Should get 404
    direct_get = await client.get(f"/api/v1/projects/{proj_a_id}", headers=headers_b)
    assert direct_get.status_code == 404
