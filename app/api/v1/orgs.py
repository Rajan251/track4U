from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import get_current_org, get_current_org_member, get_current_user, get_db
from app.models.org import Organization, OrgMember
from app.models.user import User
from app.schemas.org import BillingRead, OrgCreate, OrgMemberInvite, OrgMemberRead, OrgRead
from app.services.email import send_email

router = APIRouter(prefix="/orgs", tags=["Organizations"])


@router.get("", response_model=List[OrgRead])
async def list_user_orgs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(Organization)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .where(OrgMember.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("", response_model=OrgRead, status_code=status.HTTP_201_CREATED)
async def create_org(
    data: OrgCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    slug = data.name.lower().replace(" ", "-") + f"-{current_user.id[:6]}"
    org = Organization(name=data.name, slug=slug)
    db.add(org)
    await db.flush()

    member = OrgMember(org_id=org.id, user_id=current_user.id, role="owner")
    db.add(member)
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/current", response_model=OrgRead)
async def get_current_organization(
    org: Organization = Depends(get_current_org),
) -> Any:
    return org


@router.get("/members", response_model=List[OrgMemberRead])
async def list_org_members(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(OrgMember).options(selectinload(OrgMember.user)).where(OrgMember.org_id == org.id)
    )
    return result.scalars().all()


@router.post("/members/invite", response_model=OrgMemberRead)
async def invite_org_member(
    data: OrgMemberInvite,
    org: Organization = Depends(get_current_org),
    current_member: OrgMember = Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if current_member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can invite members",
        )

    # Check if target user exists or create dummy
    result = await db.execute(select(User).where(User.email == data.email))
    target_user = result.scalar_one_or_none()

    if not target_user:
        # Stub creation for invited user
        from app.core.security import hash_password

        target_user = User(
            email=data.email,
            hashed_password=hash_password("TemporaryPassword123!"),
            full_name=data.email.split("@")[0].title(),
        )
        db.add(target_user)
        await db.flush()

    # Check existing membership
    existing_mem = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org.id, OrgMember.user_id == target_user.id)
    )
    if existing_mem.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization",
        )

    new_member = OrgMember(org_id=org.id, user_id=target_user.id, role=data.role)
    db.add(new_member)

    # Send invitation email (stub/real SMTP)
    await send_email(
        to_email=data.email,
        subject=f"Invitation to join {org.name}",
        body=f"You have been invited to join {org.name} as a {data.role}. Please log in to access your projects.",
    )

    await db.commit()

    # Reload with user relationship
    result = await db.execute(
        select(OrgMember).options(selectinload(OrgMember.user)).where(OrgMember.id == new_member.id)
    )
    return result.scalar_one()


@router.get("/billing", response_model=BillingRead)
async def get_org_billing(
    org: Organization = Depends(get_current_org),
) -> Any:
    # TODO: integrate Stripe payment gateway here in production
    return BillingRead(
        org_id=org.id,
        plan_type=org.plan_type,
        subscription_status=org.subscription_status,
        alert_threshold_days=settings.ALERT_THRESHOLD_DAYS,
    )
