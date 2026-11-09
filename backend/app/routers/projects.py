"""
Projects API router — CRUD operations for simulation projects.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from ..database import get_db, Project, ProjectFile, SimulationJob
from ..models import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Create a new simulation project."""
    db_project = Project(
        name=project.name,
        description=project.description,
        simulation_type=project.simulation_type,
        scientific_objective=project.scientific_objective,
    )
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)

    return ProjectResponse(
        id=db_project.id,
        name=db_project.name,
        description=db_project.description,
        simulation_type=db_project.simulation_type,
        scientific_objective=db_project.scientific_objective,
        created_at=db_project.created_at,
        updated_at=db_project.updated_at,
        file_count=0,
        job_count=0,
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects."""
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()

    responses = []
    for p in projects:
        # Count files and jobs
        file_count = await db.scalar(
            select(func.count()).where(ProjectFile.project_id == p.id)
        )
        job_count = await db.scalar(
            select(func.count()).where(SimulationJob.project_id == p.id)
        )
        responses.append(ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            simulation_type=p.simulation_type,
            scientific_objective=p.scientific_objective,
            created_at=p.created_at,
            updated_at=p.updated_at,
            file_count=file_count or 0,
            job_count=job_count or 0,
        ))

    return responses


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_count = await db.scalar(
        select(func.count()).where(ProjectFile.project_id == project_id)
    )
    job_count = await db.scalar(
        select(func.count()).where(SimulationJob.project_id == project_id)
    )

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        simulation_type=project.simulation_type,
        scientific_objective=project.scientific_objective,
        created_at=project.created_at,
        updated_at=project.updated_at,
        file_count=file_count or 0,
        job_count=job_count or 0,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, update: ProjectUpdate,
                          db: AsyncSession = Depends(get_db)):
    """Update a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        simulation_type=project.simulation_type,
        scientific_objective=project.scientific_objective,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a project and all its data."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()

    # Also clean up files on disk
    import shutil
    from ..config import PROJECTS_DIR
    project_dir = PROJECTS_DIR / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir, ignore_errors=True)

    return {"status": "deleted", "project_id": project_id}
