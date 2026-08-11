from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas.auth import UserRead


class OrgCreate(BaseModel):
    name: str


class OrgRead(BaseModel):
    id: str
    name: str
    slug: str
    subscription_status: str
    plan_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrgMemberRead(BaseModel):
    id: str
    org_id: str
    user_id: str
    role: str
    user: UserRead

    model_config = ConfigDict(from_attributes=True)


class OrgMemberInvite(BaseModel):
    email: EmailStr
    role: str = "member"


class BillingRead(BaseModel):
    org_id: str
    plan_type: str
    subscription_status: str
    alert_threshold_days: int
