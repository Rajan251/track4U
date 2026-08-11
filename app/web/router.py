from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import get_current_org, get_current_user_optional, get_db
from app.models.project import Project
from app.models.task import ActivityLog, Comment, Task
from app.models.user import User
from app.models.reminder import CustomReminder
from app.models.website import TrackedWebsite

templates = Jinja2Templates(directory="app/templates")
web_router = APIRouter()


@web_router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if current_user:
        return RedirectResponse(url="/projects-view", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@web_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request, "current_user": None})


@web_router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse(
        "auth/signup.html", {"request": request, "current_user": None}
    )


@web_router.get("/projects-view", response_class=HTMLResponse)
async def projects_dashboard(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    current_org = await get_current_org(request, current_user, None, None, db)

    res = await db.execute(
        select(Project).options(selectinload(Project.tasks)).where(Project.org_id == current_org.id)
    )
    projects = res.scalars().all()

    return templates.TemplateResponse(
        "projects/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "current_org": current_org,
            "active_page": "projects",
            "projects": projects,
        },
    )


@web_router.get("/projects-view/{project_id}", response_class=HTMLResponse)
async def project_detail_kanban(
    project_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    current_org = await get_current_org(request, current_user, None, None, db)

    p_res = await db.execute(
        select(Project).where(Project.id == project_id, Project.org_id == current_org.id)
    )
    project = p_res.scalar_one_or_none()
    if not project:
        return RedirectResponse(url="/projects-view", status_code=status.HTTP_302_FOUND)

    t_res = await db.execute(
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.labels),
        )
        .where(Task.project_id == project.id, Task.org_id == current_org.id)
    )
    tasks = t_res.scalars().all()

    todo_tasks = [t for t in tasks if t.status == "todo"]
    in_progress_tasks = [t for t in tasks if t.status == "in_progress"]
    done_tasks = [t for t in tasks if t.status == "done"]

    return templates.TemplateResponse(
        "projects/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "current_org": current_org,
            "active_page": "projects",
            "project": project,
            "todo_tasks": todo_tasks,
            "in_progress_tasks": in_progress_tasks,
            "done_tasks": done_tasks,
        },
    )


@web_router.get("/tasks-view/{task_id}", response_class=HTMLResponse)
async def task_detail_view(
    task_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    current_org = await get_current_org(request, current_user, None, None, db)

    t_res = await db.execute(
        select(Task)
        .options(
            selectinload(Task.creator),
            selectinload(Task.assignee),
            selectinload(Task.labels),
            selectinload(Task.comments).selectinload(Comment.author),
            selectinload(Task.activity_logs).selectinload(ActivityLog.user),
        )
        .where(Task.id == task_id, Task.org_id == current_org.id)
    )
    task = t_res.scalar_one_or_none()
    if not task:
        return RedirectResponse(url="/projects-view", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        "tasks/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "current_org": current_org,
            "active_page": "projects",
            "task": task,
        },
    )


@web_router.get("/websites-view", response_class=HTMLResponse)
async def websites_dashboard(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    current_org = await get_current_org(request, current_user, None, None, db)

    res = await db.execute(select(TrackedWebsite).where(TrackedWebsite.org_id == current_org.id))
    websites = res.scalars().all()

    today = date.today()
    for w in websites:
        if w.domain_expiry_date:
            w.domain_days_remaining = (w.domain_expiry_date - today).days
        else:
            w.domain_days_remaining = None

        if w.ssl_expiry_date:
            w.ssl_days_remaining = (w.ssl_expiry_date - today).days
        else:
            w.ssl_days_remaining = None

    return templates.TemplateResponse(
        "websites/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "current_org": current_org,
            "active_page": "websites",
            "websites": websites,
            "threshold_days": settings.ALERT_THRESHOLD_DAYS,
            "internal_token": settings.INTERNAL_API_TOKEN,
        },
    )


@web_router.get("/websites-view/{website_id}", response_class=HTMLResponse)
async def website_detail_view(
    website_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    current_org = await get_current_org(request, current_user, None, None, db)

    res = await db.execute(
        select(TrackedWebsite)
        .options(selectinload(TrackedWebsite.alert_logs))
        .where(TrackedWebsite.id == website_id, TrackedWebsite.org_id == current_org.id)
    )
    website = res.scalar_one_or_none()
    if not website:
        return RedirectResponse(url="/websites-view", status_code=status.HTTP_302_FOUND)

    today = date.today()
    if website.domain_expiry_date:
        website.domain_days_remaining = (website.domain_expiry_date - today).days
    else:
        website.domain_days_remaining = None

    if website.ssl_expiry_date:
        website.ssl_days_remaining = (website.ssl_expiry_date - today).days
    else:
        website.ssl_days_remaining = None

    return templates.TemplateResponse(
        "websites/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "current_org": current_org,
            "active_page": "websites",
            "website": website,
        },
    )


@web_router.get("/settings-view", response_class=HTMLResponse)
async def settings_view(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    current_org = await get_current_org(request, current_user, None, None, db)

    return templates.TemplateResponse(
        "websites/settings.html",
        {
            "request": request,
            "current_user": current_user,
            "current_org": current_org,
            "active_page": "settings",
            "threshold_days": settings.ALERT_THRESHOLD_DAYS,
            "internal_token": settings.INTERNAL_API_TOKEN,
        },
    )


@web_router.get("/reminders-view", response_class=HTMLResponse)
async def reminders_dashboard(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    current_org = await get_current_org(request, current_user, None, None, db)

    res = await db.execute(
        select(CustomReminder)
        .options(selectinload(CustomReminder.alert_logs))
        .where(
            CustomReminder.org_id == current_org.id,
            CustomReminder.user_id == current_user.id,
        )
        .order_by(CustomReminder.target_date.asc())
    )
    reminders = res.scalars().all()

    today = date.today()
    for r in reminders:
        r.days_remaining = (r.target_date - today).days

    return templates.TemplateResponse(
        "reminders/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "current_org": current_org,
            "active_page": "reminders",
            "reminders": reminders,
        },
    )
