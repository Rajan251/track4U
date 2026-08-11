from datetime import date
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_org, get_current_user, get_db
from app.models.org import Organization
from app.models.user import User
from app.models.website import TrackedWebsite
from app.schemas.website import (
    TrackedWebsiteCreate,
    TrackedWebsiteRead,
    TrackedWebsiteUpdate,
)
from app.services.website_check import check_single_website

router = APIRouter(prefix="/websites", tags=["Website Expiry Tracker"])


def compute_remaining_days(website: TrackedWebsite) -> TrackedWebsiteRead:
    read_obj = TrackedWebsiteRead.model_validate(website)
    today = date.today()
    if website.domain_expiry_date:
        read_obj.domain_days_remaining = (website.domain_expiry_date - today).days
    if website.ssl_expiry_date:
        read_obj.ssl_days_remaining = (website.ssl_expiry_date - today).days
    return read_obj


@router.get("", response_model=List[TrackedWebsiteRead])
async def list_tracked_websites(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(TrackedWebsite)
        .options(selectinload(TrackedWebsite.alert_logs))
        .where(TrackedWebsite.org_id == org.id)
    )
    websites = result.scalars().all()
    return [compute_remaining_days(w) for w in websites]


@router.post("", response_model=TrackedWebsiteRead, status_code=status.HTTP_201_CREATED)
async def add_tracked_website(
    data: TrackedWebsiteCreate,
    org: Organization = Depends(get_current_org),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    website = TrackedWebsite(
        org_id=org.id,
        added_by=current_user.id,
        url=data.url,
        label=data.label,
        is_active=True,
    )
    db.add(website)
    await db.commit()

    # Immediate check so the user sees status right away!
    await check_single_website(db, website)

    res = await db.execute(
        select(TrackedWebsite)
        .options(selectinload(TrackedWebsite.alert_logs))
        .where(TrackedWebsite.id == website.id)
    )
    website = res.scalar_one()
    return compute_remaining_days(website)


@router.get("/{website_id}", response_model=TrackedWebsiteRead)
async def get_tracked_website(
    website_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(TrackedWebsite)
        .options(selectinload(TrackedWebsite.alert_logs))
        .where(TrackedWebsite.id == website_id, TrackedWebsite.org_id == org.id)
    )
    website = result.scalar_one_or_none()
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tracked website not found"
        )
    return compute_remaining_days(website)


@router.patch("/{website_id}", response_model=TrackedWebsiteRead)
async def update_tracked_website(
    website_id: str,
    data: TrackedWebsiteUpdate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(TrackedWebsite)
        .options(selectinload(TrackedWebsite.alert_logs))
        .where(TrackedWebsite.id == website_id, TrackedWebsite.org_id == org.id)
    )
    website = result.scalar_one_or_none()
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tracked website not found"
        )

    if data.label is not None:
        website.label = data.label
    if data.is_active is not None:
        website.is_active = data.is_active

    await db.commit()

    res = await db.execute(
        select(TrackedWebsite)
        .options(selectinload(TrackedWebsite.alert_logs))
        .where(TrackedWebsite.id == website.id)
    )
    website = res.scalar_one()
    return compute_remaining_days(website)


@router.delete("/{website_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_tracked_website(
    website_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(TrackedWebsite).where(
            TrackedWebsite.id == website_id, TrackedWebsite.org_id == org.id
        )
    )
    website = result.scalar_one_or_none()
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tracked website not found"
        )

    await db.delete(website)
    await db.commit()
    from fastapi import Response

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{website_id}/check-now", response_model=TrackedWebsiteRead)
async def check_website_now(
    website_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(TrackedWebsite)
        .options(selectinload(TrackedWebsite.alert_logs))
        .where(TrackedWebsite.id == website_id, TrackedWebsite.org_id == org.id)
    )
    website = result.scalar_one_or_none()
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tracked website not found"
        )

    await check_single_website(db, website)

    res = await db.execute(
        select(TrackedWebsite)
        .options(selectinload(TrackedWebsite.alert_logs))
        .where(TrackedWebsite.id == website.id)
    )
    website = res.scalar_one()
    return compute_remaining_days(website)
