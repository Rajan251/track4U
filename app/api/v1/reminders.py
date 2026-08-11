from datetime import date
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_org, get_current_user, get_db
from app.models.org import Organization
from app.models.reminder import CustomReminder
from app.models.user import User
from app.schemas.reminder import CustomReminderCreate, CustomReminderRead, CustomReminderUpdate

router = APIRouter(prefix="/reminders", tags=["Custom Reminders"])


def _add_days_remaining(reminder: CustomReminder) -> CustomReminderRead:
    """Attach computed days_remaining field to the schema output."""
    obj = CustomReminderRead.model_validate(reminder)
    obj.days_remaining = (reminder.target_date - date.today()).days
    return obj


@router.get("", response_model=List[CustomReminderRead])
async def list_reminders(
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all reminders for the current user in the current org."""
    result = await db.execute(
        select(CustomReminder)
        .options(selectinload(CustomReminder.alert_logs))
        .where(
            CustomReminder.org_id == org.id,
            CustomReminder.user_id == current_user.id,
        )
        .order_by(CustomReminder.target_date.asc())
    )
    reminders = result.scalars().all()
    return [_add_days_remaining(r) for r in reminders]


@router.post("", response_model=CustomReminderRead, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    data: CustomReminderCreate,
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new custom reminder."""
    reminder = CustomReminder(
        org_id=org.id,
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        target_date=data.target_date,
        remind_days_before=data.remind_days_before,
        repeat_interval_days=data.repeat_interval_days,
        is_active=True,
        alert_emails=data.alert_emails,
    )
    db.add(reminder)
    await db.commit()

    res = await db.execute(
        select(CustomReminder)
        .options(selectinload(CustomReminder.alert_logs))
        .where(CustomReminder.id == reminder.id)
    )
    reminder = res.scalar_one()
    return _add_days_remaining(reminder)


@router.get("/{reminder_id}", response_model=CustomReminderRead)
async def get_reminder(
    reminder_id: str,
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(CustomReminder)
        .options(selectinload(CustomReminder.alert_logs))
        .where(
            CustomReminder.id == reminder_id,
            CustomReminder.org_id == org.id,
            CustomReminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return _add_days_remaining(reminder)


@router.patch("/{reminder_id}", response_model=CustomReminderRead)
async def update_reminder(
    reminder_id: str,
    data: CustomReminderUpdate,
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(CustomReminder)
        .options(selectinload(CustomReminder.alert_logs))
        .where(
            CustomReminder.id == reminder_id,
            CustomReminder.org_id == org.id,
            CustomReminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")

    if data.title is not None:
        reminder.title = data.title.strip()
    if data.description is not None:
        reminder.description = data.description
    if data.target_date is not None:
        reminder.target_date = data.target_date
    if data.remind_days_before is not None:
        reminder.remind_days_before = data.remind_days_before
    if data.repeat_interval_days is not None:
        reminder.repeat_interval_days = data.repeat_interval_days
    if data.is_active is not None:
        reminder.is_active = data.is_active
    if data.alert_emails is not None:
        reminder.alert_emails = data.alert_emails if data.alert_emails.strip() else None

    await db.commit()

    res = await db.execute(
        select(CustomReminder)
        .options(selectinload(CustomReminder.alert_logs))
        .where(CustomReminder.id == reminder.id)
    )
    reminder = res.scalar_one()
    return _add_days_remaining(reminder)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_reminder(
    reminder_id: str,
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(CustomReminder).where(
            CustomReminder.id == reminder_id,
            CustomReminder.org_id == org.id,
            CustomReminder.user_id == current_user.id,
        )
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")

    await db.delete(reminder)
    await db.commit()
    from fastapi import Response

    return Response(status_code=status.HTTP_204_NO_CONTENT)
