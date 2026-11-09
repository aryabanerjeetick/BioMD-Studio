"""
Simulation API router — configure and run MD simulations.
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from ..database import get_db, Project, ProjectFile, SimulationJob, JobStatus, AsyncSessionLocal
from ..models import SimulationConfig, JobResponse
from ..services.job_manager import start_simulation, cancel_simulation, get_active_job_count
from ..config import gromacs, PROJECTS_DIR, MAX_CONCURRENT_JOBS, FORCE_FIELD_INFO, WATER_MODEL_INFO

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


@router.get("/system-status")
async def get_system_status():
    """Get system capabilities and GROMACS availability."""
    from ..services.analysis_engine import MDTRAJ_AVAILABLE, MDTRAJ_VERSION
    return {
        "gromacs": gromacs.to_dict(),
        "mdtraj": {
            "available": MDTRAJ_AVAILABLE,
            "version": MDTRAJ_VERSION,
        },
        "force_fields": FORCE_FIELD_INFO,
        "water_models": WATER_MODEL_INFO,
        "limits": {
            "max_concurrent_jobs": MAX_CONCURRENT_JOBS,
            "active_jobs": get_active_job_count(),
        },
    }


@router.post("/start/{project_id}", response_model=JobResponse)
async def start_simulation_job(
    project_id: str,
    config: SimulationConfig,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new MD simulation for a project.
    Requires GROMACS to be available. Will NOT fabricate results.
    """
    # Check GROMACS availability
    if not gromacs.available:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "GROMACS is not installed on this server",
                "message": (
                    "GROMACS is required to run MD simulations. "
                    "Please install GROMACS (https://www.gromacs.org/) or "
                    "use the Google Colab backend which includes GROMACS with free GPU. "
                    "See the README for setup instructions."
                ),
                "gromacs_available": False,
            }
        )

    # Check concurrent job limit
    if get_active_job_count() >= MAX_CONCURRENT_JOBS:
        raise HTTPException(
            status_code=429,
            detail=f"Maximum concurrent jobs ({MAX_CONCURRENT_JOBS}) reached. Please wait."
        )

    # Verify project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Find protein file
    result = await db.execute(
        select(ProjectFile).where(
            ProjectFile.project_id == project_id,
            ProjectFile.file_role.in_(["protein", "complex"]),
            ProjectFile.validation_status == "valid",
        )
    )
    protein_file = result.scalar_one_or_none()
    if not protein_file:
        raise HTTPException(
            status_code=400,
            detail="No validated protein structure found. Upload and validate a PDB file first."
        )

    # Find ligand file (optional)
    result = await db.execute(
        select(ProjectFile).where(
            ProjectFile.project_id == project_id,
            ProjectFile.file_role == "ligand",
        )
    )
    ligand_file = result.scalar_one_or_none()

    # Validate force field compatibility
    ff_info = FORCE_FIELD_INFO.get(config.force_field)
    if not ff_info:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown force field: {config.force_field}. "
                   f"Available: {list(FORCE_FIELD_INFO.keys())}"
        )
    if config.water_model not in ff_info["water_models"]:
        raise HTTPException(
            status_code=400,
            detail=f"Water model '{config.water_model}' is not compatible with "
                   f"force field '{config.force_field}'. "
                   f"Compatible: {ff_info['water_models']}"
        )

    # Create job record
    job = SimulationJob(
        project_id=project_id,
        status=JobStatus.CREATED.value,
        force_field=config.force_field,
        water_model=config.water_model,
        box_type=config.box_type,
        box_distance=config.box_distance,
        salt_concentration=config.salt_concentration,
        cation=config.cation,
        anion=config.anion,
        em_steps=config.em_steps,
        em_tol=config.em_tol,
        nvt_steps=config.nvt_steps,
        npt_steps=config.npt_steps,
        eq_temperature=config.temperature,
        eq_pressure=config.pressure,
        eq_dt=config.dt,
        prod_steps=config.prod_steps,
        prod_dt=config.dt,
        prod_temperature=config.temperature,
        prod_pressure=config.pressure,
        nstxout_compressed=config.nstxout_compressed,
        nstenergy=config.nstenergy,
        thermostat=config.thermostat,
        barostat=config.barostat,
        constraints=config.constraints,
        electrostatics=config.electrostatics,
        vdw_cutoff=config.vdw_cutoff,
        coulomb_cutoff=config.coulomb_cutoff,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Start simulation in background
    sim_config = config.model_dump()
    start_simulation(
        job_id=job.id,
        project_id=project_id,
        protein_pdb=protein_file.disk_path,
        config=sim_config,
        db_session_factory=AsyncSessionLocal,
        ligand_pdb=ligand_file.disk_path if ligand_file else None,
    )

    return JobResponse(
        id=job.id,
        project_id=job.project_id,
        status=job.status,
        current_stage=job.current_stage,
        progress_percent=job.progress_percent,
        force_field=job.force_field,
        water_model=job.water_model,
        n_total_atoms=job.n_total_atoms,
        started_at=job.started_at,
        completed_at=job.completed_at,
        elapsed_seconds=job.elapsed_seconds,
        error_message=job.error_message,
        error_stage=job.error_stage,
        warnings=job.warnings or [],
        gromacs_version=job.gromacs_version,
        em_initial_energy=job.em_initial_energy,
        em_final_energy=job.em_final_energy,
        em_converged=job.em_converged,
        created_at=job.created_at,
    )


@router.get("/jobs/{project_id}", response_model=list[JobResponse])
async def list_jobs(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all simulation jobs for a project."""
    result = await db.execute(
        select(SimulationJob).where(SimulationJob.project_id == project_id)
        .order_by(SimulationJob.created_at.desc())
    )
    jobs = result.scalars().all()

    return [JobResponse(
        id=j.id,
        project_id=j.project_id,
        status=j.status,
        current_stage=j.current_stage,
        progress_percent=j.progress_percent,
        force_field=j.force_field,
        water_model=j.water_model,
        n_total_atoms=j.n_total_atoms,
        started_at=j.started_at,
        completed_at=j.completed_at,
        elapsed_seconds=j.elapsed_seconds,
        error_message=j.error_message,
        error_stage=j.error_stage,
        warnings=j.warnings or [],
        gromacs_version=j.gromacs_version,
        em_initial_energy=j.em_initial_energy,
        em_final_energy=j.em_final_energy,
        em_converged=j.em_converged,
        created_at=j.created_at,
    ) for j in jobs]


@router.get("/job/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific job's status and results."""
    result = await db.execute(select(SimulationJob).where(SimulationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=job.id,
        project_id=job.project_id,
        status=job.status,
        current_stage=job.current_stage,
        progress_percent=job.progress_percent,
        force_field=job.force_field,
        water_model=job.water_model,
        n_total_atoms=job.n_total_atoms,
        started_at=job.started_at,
        completed_at=job.completed_at,
        elapsed_seconds=job.elapsed_seconds,
        error_message=job.error_message,
        error_stage=job.error_stage,
        warnings=job.warnings or [],
        gromacs_version=job.gromacs_version,
        em_initial_energy=job.em_initial_energy,
        em_final_energy=job.em_final_energy,
        em_converged=job.em_converged,
        created_at=job.created_at,
    )


@router.post("/cancel/{job_id}")
async def cancel_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel a running simulation."""
    result = await db.execute(select(SimulationJob).where(SimulationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value):
        raise HTTPException(status_code=400, detail=f"Job already {job.status}")

    cancelled = cancel_simulation(job_id)
    if cancelled:
        job.status = JobStatus.CANCELLED.value
        await db.commit()
        return {"status": "cancelled", "job_id": job_id}
    else:
        raise HTTPException(status_code=400, detail="Could not cancel job — it may have already finished")
