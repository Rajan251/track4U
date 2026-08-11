from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class TrackedWebsiteCreate(BaseModel):
    url: str
    label: Optional[str] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("http://") and not v.startswith("https://"):
            v = f"https://{v}"
        return v


class TrackedWebsiteUpdate(BaseModel):
    label: Optional[str] = None
    is_active: Optional[bool] = None


class ExpiryAlertLogRead(BaseModel):
    id: str
    tracked_website_id: str
    alert_type: str
    days_remaining_at_alert: int
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrackedWebsiteRead(BaseModel):
    id: str
    org_id: str
    added_by: str
    url: str
    label: Optional[str] = None
    domain_expiry_date: Optional[date] = None
    ssl_expiry_date: Optional[date] = None
    last_checked_at: Optional[datetime] = None
    last_check_status: Optional[str] = None
    last_check_error: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Calculated properties
    domain_days_remaining: Optional[int] = None
    ssl_days_remaining: Optional[int] = None
    alert_logs: List[ExpiryAlertLogRead] = []

    model_config = ConfigDict(from_attributes=True)
