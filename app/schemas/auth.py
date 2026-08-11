from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    org_name: Optional[str] = "My Organization"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: str
    email: str
    full_name: str
    notify_on_expiry: bool

    model_config = ConfigDict(from_attributes=True)


class UserUpdateSettings(BaseModel):
    notify_on_expiry: bool
