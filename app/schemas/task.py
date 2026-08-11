from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.auth import UserRead


class LabelCreate(BaseModel):
    name: str
    color: Optional[str] = "#3B82F6"


class LabelRead(BaseModel):
    id: str
    org_id: str
    name: str
    color: str

    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    content: str


class CommentRead(BaseModel):
    id: str
    task_id: str
    author_id: str
    content: str
    created_at: datetime
    author: Optional[UserRead] = None

    model_config = ConfigDict(from_attributes=True)


class ActivityLogRead(BaseModel):
    id: str
    task_id: str
    user_id: str
    action: str
    details: Optional[str] = None
    created_at: datetime
    user: Optional[UserRead] = None

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    status: Optional[str] = "todo"
    priority: Optional[str] = "medium"
    due_date: Optional[date] = None
    assignee_id: Optional[str] = None
    label_ids: Optional[List[str]] = []
    alert_emails: Optional[str] = None          # comma-separated extra alert recipients
    alert_days_before: Optional[int] = 3         # days before due_date to start alerting


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    assignee_id: Optional[str] = None
    label_ids: Optional[List[str]] = None
    alert_emails: Optional[str] = None
    alert_days_before: Optional[int] = None


class TaskRead(BaseModel):
    id: str
    project_id: str
    org_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    due_date: Optional[date] = None
    assignee_id: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    alert_emails: Optional[str] = None
    alert_days_before: int = 3

    assignee: Optional[UserRead] = None
    creator: Optional[UserRead] = None
    labels: List[LabelRead] = []
    comments: List[CommentRead] = []
    activity_logs: List[ActivityLogRead] = []

    model_config = ConfigDict(from_attributes=True)
