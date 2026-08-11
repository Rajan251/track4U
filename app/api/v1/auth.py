from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.org import Organization, OrgMember
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLogin, UserRead, UserSignup, UserUpdateSettings

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    data: UserSignup,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Any:
    # Check if user exists
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Create User
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.flush()

    # Create Default Organization
    org_name = data.org_name or "My Organization"
    slug = org_name.lower().replace(" ", "-") + f"-{user.id[:8]}"
    org = Organization(name=org_name, slug=slug)
    db.add(org)
    await db.flush()

    # Add User as Owner
    member = OrgMember(org_id=org.id, user_id=user.id, role="owner")
    db.add(member)

    await db.commit()

    token = create_access_token(subject=user.id)
    response.set_cookie(
        key="access_token", value=token, httponly=True, max_age=86400, samesite="lax"
    )
    response.set_cookie(
        key="active_org_id", value=org.id, httponly=True, max_age=86400, samesite="lax"
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token(subject=user.id)

    # Get user's first org
    org_result = await db.execute(
        select(Organization)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .where(OrgMember.user_id == user.id)
    )
    org = org_result.scalar_one_or_none()

    response.set_cookie(
        key="access_token", value=token, httponly=True, max_age=86400, samesite="lax"
    )
    if org:
        response.set_cookie(
            key="active_org_id", value=org.id, httponly=True, max_age=86400, samesite="lax"
        )

    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response) -> Any:
    response.delete_cookie("access_token")
    response.delete_cookie("active_org_id")
    return {"detail": "Logged out successfully"}


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)) -> Any:
    return current_user


@router.patch("/me/settings", response_model=UserRead)
async def update_settings(
    data: UserUpdateSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    current_user.notify_on_expiry = data.notify_on_expiry
    await db.commit()
    await db.refresh(current_user)
    return current_user
