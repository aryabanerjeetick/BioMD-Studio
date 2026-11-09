"""
Analysis API router — run and retrieve trajectory analyses.
All results come from REAL computations on actual trajectory data.
"""

import os
import json
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db, SimulationJob, ProjectFile
from ..models import AnalysisRequest, AnalysisResult
from ..services.analysis_engine import run_analysis, MDTRAJ_AVAILABLE
from ..config import PROJECTS_DIR

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/available")
async def list_available_analyses():
    """List available analysis types and their parameters."""
    analyses = {
        "rmsd": {
            "name": "Root Mean Square Deviation",
            "description": "Measures structural deviation from reference over time",
            "parameters": {
                "atom_selection": {
                    "type": "string",
                    "default": "backbone",
                    "options": ["backbone", "ca", "heavy", "protein"],
                    "description": "Atom selection for RMSD calculation"
                },
                "stride": {"type": "integer", "default": 1, "description": "Frame stride"}
            },
            "requires_trajectory": True,
            "available": MDTRAJ_AVAILABLE,
        },
        "rmsf": {
            "name": "Root Mean Square Fluctuation",
            "description": "Per-residue structural fluctuation",
            "parameters": {
                "atom_selection": {
                    "type": "string", "default": "name CA",
                    "description": "Atom selection (default: C-alpha)"
                },
            },
            "requires_trajectory": True,
            "available": MDTRAJ_AVAILABLE,
        },
        "radius_of_gyration": {
            "name": "Radius of Gyration",
            "description": "Measures protein compactness over time",
            "parameters": {},
            "requires_trajectory": True,
            "available": MDTRAJ_AVAILABLE,
        },
        "hydrogen_bonds": {
            "name": "Hydrogen Bond Analysis",
            "description": "Counts and identifies hydrogen bonds using Baker-Hubbard criteria",
            "parameters": {
                "freq_cutoff": {"type": "float", "default": 0.1, "description": "Minimum occupancy to report"},
            },
            "requires_trajectory": True,
            "available": MDTRAJ_AVAILABLE,
        },
        "sasa": {
            "name": "Solvent Accessible Surface Area",
            "description": "Computes SASA using Shrake-Rupley algorithm",
            "parameters": {
                "probe_radius": {"type": "float", "default": 0.14, "description": "Probe radius in nm"},
                "mode": {"type": "string", "default": "total", "options": ["total", "residue", "both"]},
            },
            "requires_trajectory": True,
            "available": MDTRAJ_AVAILABLE,
        },
        "secondary_structure": {
            "name": "Secondary Structure (DSSP)",
            "description": "Assigns secondary structure per residue per frame",
            "parameters": {},
            "requires_trajectory": True,
            "available": MDTRAJ_AVAILABLE,
        },
        "pca": {
            "name": "Principal Component Analysis",
            "description": "Essential dynamics via PCA of atomic coordinates",
            "parameters": {
                "atom_selection": {"type": "string", "default": "name CA"},
                "n_components": {"type": "integer", "default": 10},
            },
            "requires_trajectory": True,
            "available": MDTRAJ_AVAILABLE,
        },
        "contact_map": {
            "name": "Contact Map",
            "description": "Residue-residue contact frequency",
            "parameters": {
                "cutoff": {"type": "float", "default": 0.45, "description": "Contact cutoff in nm"},
            },
            "requires_trajectory": True,
            "available": MDTRAJ_AVAILABLE,
        },
        "ramachandran": {
            "name": "Ramachandran Plot",
            "description": "Phi/Psi dihedral angle distribution",
            "parameters": {},
            "requires_trajectory": True,
            "available": MDTRAJ_AVAILABLE,
        },
        "clustering": {
            "name": "RMSD Clustering",
            "description": "Cluster trajectory frames by structural similarity",
            "parameters": {
                "rmsd_cutoff": {"type": "float", "default": 0.2, "description": "RMSD cutoff in nm"},
                "atom_selection": {"type": "string", "default": "name CA"},
            },
            "requires_trajectory": True,
            "available": MDTRAJ_AVAILABLE,
        },
    }
    return analyses


@router.post("/run/{job_id}")
async def run_analysis_on_job(
    job_id: str,
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Run an analysis on a completed simulation's trajectory.
    Results are computed from ACTUAL trajectory data.
    """
    if not MDTRAJ_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="MDTraj is not installed. Install with: pip install mdtraj"
        )

    # Get job
    result = await db.execute(select(SimulationJob).where(SimulationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("completed", "completed_with_warnings"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot analyze job with status '{job.status}'. "
                   f"Simulation must be completed first."
        )

    # Find trajectory and topology files
    work_dir = job.work_dir
    if not work_dir or not os.path.exists(work_dir):
        raise HTTPException(status_code=404, detail="Job work directory not found")

    # Look for trajectory files
    traj_path = None
    for ext in ["xtc", "trr"]:
        candidate = os.path.join(work_dir, f"prod.{ext}")
        if os.path.exists(candidate):
            traj_path = candidate
            break

    if not traj_path:
        raise HTTPException(
            status_code=404,
            detail="No trajectory file found. The production MD may not have completed."
        )

    # Look for topology
    top_path = None
    for name in ["prod.gro", "npt.gro", "protein_processed.gro"]:
        candidate = os.path.join(work_dir, name)
        if os.path.exists(candidate):
            top_path = candidate
            break

    if not top_path:
        raise HTTPException(
            status_code=404,
            detail="No topology/structure file found for trajectory analysis."
        )

    # Run the analysis
    analysis_result = run_analysis(
        analysis_type=request.analysis_type,
        traj_path=traj_path,
        top_path=top_path,
        parameters=request.parameters,
    )

    # Store result in job
    if job.analysis_results is None:
        job.analysis_results = {}
    job.analysis_results[request.analysis_type] = analysis_result
    await db.commit()

    return analysis_result


@router.post("/run-on-file")
async def run_analysis_on_uploaded_files(
    request: AnalysisRequest,
    trajectory_file_id: str = Query(...),
    topology_file_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Run analysis on uploaded trajectory and topology files.
    For users who have pre-existing MD trajectories.
    """
    if not MDTRAJ_AVAILABLE:
        raise HTTPException(status_code=503, detail="MDTraj not available")

    # Get files
    traj_result = await db.execute(select(ProjectFile).where(ProjectFile.id == trajectory_file_id))
    traj_file = traj_result.scalar_one_or_none()
    if not traj_file:
        raise HTTPException(status_code=404, detail="Trajectory file not found")

    top_result = await db.execute(select(ProjectFile).where(ProjectFile.id == topology_file_id))
    top_file = top_result.scalar_one_or_none()
    if not top_file:
        raise HTTPException(status_code=404, detail="Topology file not found")

    return run_analysis(
        analysis_type=request.analysis_type,
        traj_path=traj_file.disk_path,
        top_path=top_file.disk_path,
        parameters=request.parameters,
    )


@router.get("/results/{job_id}")
async def get_all_results(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get all stored analysis results for a job."""
    result = await db.execute(select(SimulationJob).where(SimulationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job_id,
        "status": job.status,
        "analyses": job.analysis_results or {},
        "em_results": {
            "initial_energy": job.em_initial_energy,
            "final_energy": job.em_final_energy,
            "max_force": job.em_max_force,
            "converged": job.em_converged,
        } if job.em_initial_energy is not None else None,
    }


@router.get("/export-csv/{job_id}/{analysis_type}")
async def export_analysis_csv(
    job_id: str, analysis_type: str,
    db: AsyncSession = Depends(get_db),
):
    """Export analysis data as CSV."""
    result = await db.execute(select(SimulationJob).where(SimulationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    analyses = job.analysis_results or {}
    if analysis_type not in analyses:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis '{analysis_type}' not found. "
                   f"Available: {list(analyses.keys()) if analyses else 'none — run analyses first'}"
        )

    data = analyses[analysis_type].get("data", {})

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Try to create a tabular format
    if "time_ps" in data:
        time = data["time_ps"]
        # Find matching data columns
        columns = {"Time (ps)": time}
        for key, values in data.items():
            if key != "time_ps" and isinstance(values, list) and len(values) == len(time):
                columns[key] = values

        writer.writerow(columns.keys())
        for i in range(len(time)):
            writer.writerow([col[i] for col in columns.values()])
    elif "residue_indices" in data:
        headers = ["Residue Index", "Residue Label"]
        values_lists = [data["residue_indices"], data.get("residue_labels", data["residue_indices"])]
        for key, vals in data.items():
            if key not in ("residue_indices", "residue_labels") and isinstance(vals, list):
                headers.append(key)
                values_lists.append(vals)
        writer.writerow(headers)
        for i in range(len(data["residue_indices"])):
            writer.writerow([vl[i] if i < len(vl) else "" for vl in values_lists])
    else:
        # Generic key-value export
        writer.writerow(["key", "value"])
        for key, value in data.items():
            if isinstance(value, (int, float, str)):
                writer.writerow([key, value])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={analysis_type}_{job_id[:8]}.csv"},
    )
