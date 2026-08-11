from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: Optional[str] = "active"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ProjectRead(BaseModel):
    id: str
    org_id: str
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
