from typing import AsyncGenerator, Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import async_session_factory
from app.models.org import Organization, OrgMember
from app.models.user import User


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user_optional(
    request: Request,
    authorization: Optional[str] = Header(None),
    access_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif access_token:
        token = access_token
    elif "Authorization" in request.headers:
        header_val = request.headers.get("Authorization", "")
        if header_val.startswith("Bearer "):
            token = header_val.split(" ")[1]

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_org(
    request: Request,
    user: User = Depends(get_current_user),
    x_org_id: Optional[str] = Header(None),
    org_id_cookie: Optional[str] = Cookie(None, alias="active_org_id"),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    # Priority: Header -> Cookie -> User's first org
    target_org_id = x_org_id or org_id_cookie

    if target_org_id:
        result = await db.execute(
            select(Organization)
            .join(OrgMember, OrgMember.org_id == Organization.id)
            .where(Organization.id == target_org_id, OrgMember.user_id == user.id)
        )
        org = result.scalar_one_or_none()
        if org:
            return org

    # Fallback to first org user belongs to
    result = await db.execute(
        select(Organization)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .where(OrgMember.user_id == user.id)
        .order_by(OrgMember.created_at.asc())
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not belong to any organization",
        )
    return org


async def get_current_org_member(
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> OrgMember:
    result = await db.execute(
        select(OrgMember).where(
            OrgMember.org_id == org.id,
            OrgMember.user_id == user.id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden for current organization",
        )
    return member
