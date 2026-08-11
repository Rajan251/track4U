from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_org, get_current_user, get_db
from app.models.org import Organization
from app.models.project import Project
from app.models.task import ActivityLog, Comment, Label, Task, TaskLabel
from app.models.user import User
from app.schemas.task import (
    CommentCreate,
    CommentRead,
    LabelCreate,
    LabelRead,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


from app.core.config import settings
from app.services.email import send_email


def task_eager_options():
    return [
        selectinload(Task.project),
        selectinload(Task.assignee),
        selectinload(Task.creator),
        selectinload(Task.labels),
        selectinload(Task.comments).selectinload(Comment.author),
        selectinload(Task.activity_logs).selectinload(ActivityLog.user),
    ]


async def send_status_change_email(
    task: Task,
    old_status: str,
    new_status: str,
    user: User,
):
    """
    Sends email notification when a task's status changes.
    Recipients include task custom alert_emails, global alert emails,
    creator, assignee, and updated-by user.
    """
    try:
        recipients = set()
        if task.alert_emails:
            for em in task.alert_emails.split(","):
                em = em.strip()
                if em:
                    recipients.add(em)
        if settings.ALERT_TO_EMAILS:
            global_emails = (
                settings.ALERT_TO_EMAILS
                if isinstance(settings.ALERT_TO_EMAILS, list)
                else settings.ALERT_TO_EMAILS.split(",")
            )
            for em in global_emails:
                em = em.strip()
                if em:
                    recipients.add(em)
        if task.creator and task.creator.email:
            recipients.add(task.creator.email.strip())
        if task.assignee and task.assignee.email:
            recipients.add(task.assignee.email.strip())
        if user and user.email:
            recipients.add(user.email.strip())

        if not recipients:
            return

        old_fmt = old_status.replace("_", " ").title()
        new_fmt = new_status.replace("_", " ").title()
        proj_name = task.project.name if task.project else "Project"

        subject = f"[Track4U Alert] Task Status Updated: {task.title} → {new_fmt}"

        body = (
            f"Task Status Change Notification\n\n"
            f"Task: {task.title}\n"
            f"Project: {proj_name}\n"
            f"Status: {old_fmt} ➔ {new_fmt}\n"
            f"Updated By: {user.full_name} ({user.email})\n"
            f"Priority: {task.priority.upper()}\n"
            f"Due Date: {task.due_date or 'None'}\n\n"
            f"Description:\n{task.description or 'No description'}\n"
        )

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #0f172a; color: #f8fafc; border-radius: 12px; border: 1px solid #1e293b;">
            <h2 style="color: #6366f1; margin-top: 0;">Task Status Updated</h2>
            <div style="background: #1e293b; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0 0 10px 0; font-size: 18px; font-weight: bold; color: #ffffff;">{task.title}</p>
                <p style="margin: 0 0 10px 0; font-size: 13px; color: #94a3b8;">Project: <strong style="color: #cbd5e1;">{proj_name}</strong></p>
                <div style="display: inline-block; padding: 6px 12px; border-radius: 6px; background: #312e81; color: #c7d2fe; font-weight: bold; font-size: 14px;">
                    {old_fmt} &nbsp;➔&nbsp; <span style="color: #4ade80;">{new_fmt}</span>
                </div>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 20px;">
                <tr><td style="padding: 8px 0; color: #94a3b8; width: 120px;">Updated By:</td><td style="color: #f8fafc;">{user.full_name} ({user.email})</td></tr>
                <tr><td style="padding: 8px 0; color: #94a3b8;">Priority:</td><td style="color: #f8fafc;"><strong style="text-transform: uppercase;">{task.priority}</strong></td></tr>
                <tr><td style="padding: 8px 0; color: #94a3b8;">Due Date:</td><td style="color: #f8fafc;">{task.due_date or 'None'}</td></tr>
            </table>
            {f'<div style="background: #1e293b; padding: 12px; border-radius: 6px; font-size: 13px; color: #cbd5e1; margin-bottom: 20px;">{task.description}</div>' if task.description else ''}
            <p style="font-size: 12px; color: #64748b; margin: 0;">This is an automated notification from Track4U Alerting System.</p>
        </div>
        """

        for recipient in recipients:
            await send_email(to_email=recipient, subject=subject, body=body, html_body=html_body)
    except Exception as e:
        logger.error(f"Failed sending task status change email: {e}")




@router.get("", response_model=List[TaskRead])
async def list_tasks(
    project_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    query = select(Task).options(*task_eager_options()).where(Task.org_id == org.id)
    if project_id:
        query = query.where(Task.project_id == project_id)
    if status_filter:
        query = query.where(Task.status == status_filter)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    # Verify project belongs to org
    proj_res = await db.execute(
        select(Project).where(Project.id == data.project_id, Project.org_id == org.id)
    )
    if not proj_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found in this organization"
        )

    task = Task(
        project_id=data.project_id,
        org_id=org.id,
        title=data.title,
        description=data.description,
        status=data.status or "todo",
        priority=data.priority or "medium",
        due_date=data.due_date,
        assignee_id=data.assignee_id,
        created_by=current_user.id,
        alert_emails=data.alert_emails,
        alert_days_before=data.alert_days_before if data.alert_days_before is not None else 3,
    )
    db.add(task)
    await db.flush()

    if data.label_ids:
        for lid in data.label_ids:
            db.add(TaskLabel(task_id=task.id, label_id=lid))

    # Activity log
    log = ActivityLog(
        task_id=task.id,
        user_id=current_user.id,
        action="created",
        details=f"Task '{task.title}' created with status '{task.status}'",
    )
    db.add(log)

    await db.commit()

    res = await db.execute(select(Task).options(*task_eager_options()).where(Task.id == task.id))
    return res.scalar_one()


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(Task).options(*task_eager_options()).where(Task.id == task_id, Task.org_id == org.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(Task).options(*task_eager_options()).where(Task.id == task_id, Task.org_id == org.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    changes = []
    old_status = task.status
    status_changed = False

    if data.title is not None and data.title != task.title:
        task.title = data.title
        changes.append("title")
    if data.description is not None:
        task.description = data.description
    if data.status is not None and data.status != task.status:
        changes.append(f"status changed from '{task.status}' to '{data.status}'")
        task.status = data.status
        status_changed = True
    if data.priority is not None and data.priority != task.priority:
        changes.append(f"priority changed to '{data.priority}'")
        task.priority = data.priority
    if data.due_date is not None:
        task.due_date = data.due_date
    if data.assignee_id is not None and data.assignee_id != task.assignee_id:
        task.assignee_id = data.assignee_id
        changes.append("assignee updated")

    if data.label_ids is not None:
        await db.execute(delete(TaskLabel).where(TaskLabel.task_id == task.id))
        for lid in data.label_ids:
            db.add(TaskLabel(task_id=task.id, label_id=lid))

    if data.alert_emails is not None:
        task.alert_emails = data.alert_emails.strip() if data.alert_emails.strip() else None
    if data.alert_days_before is not None:
        task.alert_days_before = data.alert_days_before

    if changes:
        log = ActivityLog(
            task_id=task.id,
            user_id=current_user.id,
            action="updated",
            details="; ".join(changes),
        )
        db.add(log)

    await db.commit()

    if status_changed:
        await send_status_change_email(task, old_status, task.status, current_user)

    res = await db.execute(select(Task).options(*task_eager_options()).where(Task.id == task.id))
    return res.scalar_one()


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_task(
    task_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Task).where(Task.id == task_id, Task.org_id == org.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    await db.delete(task)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{task_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def add_comment(
    task_id: str,
    data: CommentCreate,
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    t_res = await db.execute(select(Task).where(Task.id == task_id, Task.org_id == org.id))
    if not t_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    comment = Comment(
        task_id=task_id,
        author_id=current_user.id,
        content=data.content,
    )
    db.add(comment)

    log = ActivityLog(
        task_id=task_id,
        user_id=current_user.id,
        action="comment_added",
        details="Added a comment",
    )
    db.add(log)

    await db.commit()

    res = await db.execute(
        select(Comment).options(selectinload(Comment.author)).where(Comment.id == comment.id)
    )
    return res.scalar_one()


@router.get("/labels/all", response_model=List[LabelRead])
async def list_org_labels(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Label).where(Label.org_id == org.id))
    return result.scalars().all()


@router.post("/labels/all", response_model=LabelRead, status_code=status.HTTP_201_CREATED)
async def create_label(
    data: LabelCreate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    label = Label(
        org_id=org.id,
        name=data.name,
        color=data.color or "#3B82F6",
    )
    db.add(label)
    await db.commit()
    await db.refresh(label)
    return label
