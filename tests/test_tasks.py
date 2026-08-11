import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_task_crud_and_comments(client: AsyncClient):
    # Signup
    res = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "taskuser@example.com",
            "password": "Password123!",
            "full_name": "Task User",
            "org_name": "Task Org",
        },
    )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create Project
    proj_resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Sprint 1",
        },
        headers=headers,
    )
    project_id = proj_resp.json()["id"]

    # Create Task
    task_resp = await client.post(
        "/api/v1/tasks",
        json={
            "project_id": project_id,
            "title": "Fix Auth Bug",
            "description": "Resolve JWT cookie issue",
            "priority": "high",
            "status": "todo",
        },
        headers=headers,
    )
    assert task_resp.status_code == 201
    task_data = task_resp.json()
    task_id = task_data["id"]
    assert task_data["title"] == "Fix Auth Bug"
    assert task_data["status"] == "todo"

    # Update Task status to in_progress
    patch_resp = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "status": "in_progress",
        },
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "in_progress"

    # Add Comment
    comment_resp = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={
            "content": "Working on this fix right now.",
        },
        headers=headers,
    )
    assert comment_resp.status_code == 201
    assert comment_resp.json()["content"] == "Working on this fix right now."

    # Get Task Detail -> Verify comment and activity log included
    detail_resp = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert len(detail_data["comments"]) == 1
    assert len(detail_data["activity_logs"]) >= 2
