from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db
from app.models.org import Organization
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=List[ProjectRead])
async def list_projects(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Project).where(Project.org_id == org.id))
    return result.scalars().all()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    project = Project(
        org_id=org.id,
        name=data.name,
        description=data.description,
        status=data.status or "active",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.org_id == org.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.org_id == org.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    if data.status is not None:
        project.status = data.status

    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_project(
    project_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.org_id == org.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    await db.delete(project)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
