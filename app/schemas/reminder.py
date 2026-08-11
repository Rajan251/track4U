from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class CustomReminderCreate(BaseModel):
    title: str
    description: Optional[str] = None
    target_date: date
    remind_days_before: int = 7
    repeat_interval_days: Optional[int] = None
    alert_emails: Optional[str] = None  # comma-separated extra recipients

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("remind_days_before")
    @classmethod
    def remind_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("remind_days_before must be >= 1")
        return v


class CustomReminderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_date: Optional[date] = None
    remind_days_before: Optional[int] = None
    repeat_interval_days: Optional[int] = None
    is_active: Optional[bool] = None
    alert_emails: Optional[str] = None


class ReminderAlertLogRead(BaseModel):
    id: str
    custom_reminder_id: str
    days_remaining_at_alert: int
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomReminderRead(BaseModel):
    id: str
    org_id: str
    user_id: str
    title: str
    description: Optional[str] = None
    target_date: date
    remind_days_before: int
    repeat_interval_days: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    alert_emails: Optional[str] = None

    # Computed
    days_remaining: Optional[int] = None
    alert_logs: list[ReminderAlertLogRead] = []

    model_config = ConfigDict(from_attributes=True)
