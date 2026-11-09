"""
Job Manager — handles the full MD simulation lifecycle.
Manages GROMACS execution pipeline: setup → minimize → equilibrate → production → analysis.
NEVER fabricates results. Reports real status from actual computation.
"""

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable

from ..config import gromacs, PROJECTS_DIR, MAX_ATOMS
from ..database import JobStatus
from .gromacs_engine import GromacsEngine, GromacsError
from .structure_validator import compute_file_checksum

logger = logging.getLogger(__name__)

# Active jobs registry
_active_jobs: dict[str, asyncio.Task] = {}
_job_callbacks: dict[str, list[Callable]] = {}


def register_status_callback(job_id: str, callback: Callable):
    """Register a callback for job status updates (used by WebSocket)."""
    if job_id not in _job_callbacks:
        _job_callbacks[job_id] = []
    _job_callbacks[job_id].append(callback)


def unregister_status_callback(job_id: str, callback: Callable):
    """Remove a status callback."""
    if job_id in _job_callbacks:
        _job_callbacks[job_id] = [cb for cb in _job_callbacks[job_id] if cb != callback]


async def _notify_status(job_id: str, status: str, stage: str,
                          progress: float, message: str):
    """Notify all registered callbacks of a status change."""
    update = {
        "job_id": job_id,
        "status": status,
        "stage": stage,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    for callback in _job_callbacks.get(job_id, []):
        try:
            await callback(update)
        except Exception as e:
            logger.error(f"Status callback error: {e}")


async def run_simulation_pipeline(
    job_id: str,
    project_id: str,
    protein_pdb: str,
    config: dict,
    db_session_factory,
    ligand_pdb: Optional[str] = None,
):
    """
    Execute the full MD simulation pipeline.
    This runs as an async task. All steps execute REAL GROMACS commands.
    """
    work_dir = str(PROJECTS_DIR / project_id / "jobs" / job_id)
    os.makedirs(work_dir, exist_ok=True)

    # Copy input files to work directory
    protein_input = os.path.join(work_dir, "protein_input.pdb")
    shutil.copy2(protein_pdb, protein_input)

    if ligand_pdb:
        ligand_input = os.path.join(work_dir, "ligand_input.pdb")
        shutil.copy2(ligand_pdb, ligand_input)

    warnings_list = []
    log_parts = []

    async def update_job(session, **kwargs):
        """Update job in database."""
        from sqlalchemy import update
        from ..database import SimulationJob
        stmt = update(SimulationJob).where(SimulationJob.id == job_id).values(
            updated_at=datetime.now(timezone.utc), **kwargs
        )
        await session.execute(stmt)
        await session.commit()

    try:
        engine = GromacsEngine(work_dir)
    except GromacsError as e:
        async with db_session_factory() as session:
            await update_job(session,
                status=JobStatus.FAILED.value,
                error_message=str(e),
                error_stage="initialization",
            )
        await _notify_status(job_id, "failed", "initialization", 0,
                             f"GROMACS not available: {e}")
        return

    force_field = config.get("force_field", "amber99sb-ildn")
    water_model = config.get("water_model", "tip3p")

    try:
        # ══════════════════════════════════════════════════════════════
        # STAGE 1: Protein processing with pdb2gmx
        # ══════════════════════════════════════════════════════════════
        async with db_session_factory() as session:
            await update_job(session,
                status=JobStatus.PREPARING_PROTEIN.value,
                current_stage="Processing protein with pdb2gmx",
                progress_percent=5.0,
                work_dir=work_dir,
                gromacs_version=gromacs.version or "unknown",
                input_checksums={"protein": compute_file_checksum(protein_input)},
            )
        await _notify_status(job_id, "running", "pdb2gmx", 5, "Processing protein structure...")

        pdb2gmx_result = await engine.pdb2gmx(protein_input, force_field, water_model, ignh=True)
        protein_gro = pdb2gmx_result["gro"]
        topol = pdb2gmx_result["top"]
        log_parts.append(f"=== pdb2gmx ===\n{pdb2gmx_result.get('log', '')}")

        # ══════════════════════════════════════════════════════════════
        # STAGE 2: Define simulation box
        # ══════════════════════════════════════════════════════════════
        async with db_session_factory() as session:
            await update_job(session,
                status=JobStatus.BUILDING_SYSTEM.value,
                current_stage="Defining simulation box",
                progress_percent=15.0,
            )
        await _notify_status(job_id, "running", "editconf", 15, "Setting up simulation box...")

        box_type = config.get("box_type", "dodecahedron")
        box_distance = config.get("box_distance", 1.0)
        editconf_result = await engine.editconf(protein_gro, box_type, box_distance)
        box_gro = editconf_result["gro"]
        log_parts.append(f"=== editconf ===\n{editconf_result.get('log', '')}")

        # ══════════════════════════════════════════════════════════════
        # STAGE 3: Solvation
        # ══════════════════════════════════════════════════════════════
        async with db_session_factory() as session:
            await update_job(session,
                current_stage="Adding solvent",
                progress_percent=20.0,
            )
        await _notify_status(job_id, "running", "solvate", 20, "Adding water molecules...")

        solv_result = await engine.solvate(box_gro, topol)
        solv_gro = solv_result["gro"]
        n_waters = solv_result.get("n_waters", 0)
        log_parts.append(f"=== solvate ===\n{solv_result.get('log', '')}")

        # ══════════════════════════════════════════════════════════════
        # STAGE 4: Add ions
        # ══════════════════════════════════════════════════════════════
        async with db_session_factory() as session:
            await update_job(session,
                current_stage="Adding ions",
                progress_percent=25.0,
                n_water_molecules=n_waters,
            )
        await _notify_status(job_id, "running", "genion", 25, "Adding ions for charge neutralization...")

        # Generate ions.mdp
        ions_mdp = engine.generate_mdp("em", {
            "em_steps": 50000, "em_tol": 1000.0,
            "vdw_cutoff": config.get("vdw_cutoff", 1.0),
            "coulomb_cutoff": config.get("coulomb_cutoff", 1.0),
        })
        ions_tpr = str(Path(work_dir) / "ions.tpr")
        await engine.grompp(ions_mdp, solv_gro, topol, ions_tpr, maxwarn=2)

        salt_conc = config.get("salt_concentration", 0.15)
        genion_result = await engine.genion(
            ions_tpr, topol,
            pname=config.get("cation", "NA"),
            nname=config.get("anion", "CL"),
            concentration=salt_conc,
        )
        ions_gro = genion_result["gro"]
        n_cations = genion_result.get("n_cations", 0)
        n_anions = genion_result.get("n_anions", 0)
        log_parts.append(f"=== genion ===\n{genion_result.get('log', '')}")

        # Count total atoms from GRO file
        n_total_atoms = 0
        try:
            with open(ions_gro, 'r') as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    n_total_atoms = int(lines[1].strip())
        except Exception:
            pass

        async with db_session_factory() as session:
            await update_job(session,
                n_ions=n_cations + n_anions,
                n_total_atoms=n_total_atoms,
            )

        if n_total_atoms > MAX_ATOMS:
            raise GromacsError(
                f"System has {n_total_atoms} atoms, exceeding limit of {MAX_ATOMS}. "
                "Reduce box size or use a smaller structure."
            )

        # ══════════════════════════════════════════════════════════════
        # STAGE 5: Energy Minimization
        # ══════════════════════════════════════════════════════════════
        async with db_session_factory() as session:
            await update_job(session,
                status=JobStatus.MINIMIZING.value,
                current_stage="Energy minimization",
                progress_percent=30.0,
                started_at=datetime.now(timezone.utc),
            )
        await _notify_status(job_id, "running", "minimization", 30, "Running energy minimization...")

        em_mdp = engine.generate_mdp("em", {
            "em_steps": config.get("em_steps", 50000),
            "em_tol": config.get("em_tol", 1000.0),
            "vdw_cutoff": config.get("vdw_cutoff", 1.0),
            "coulomb_cutoff": config.get("coulomb_cutoff", 1.0),
        })
        em_tpr = str(Path(work_dir) / "em.tpr")
        await engine.grompp(em_mdp, ions_gro, topol, em_tpr, maxwarn=2)

        em_result = await engine.mdrun(em_tpr, "em")
        log_parts.append(f"=== Energy Minimization ===\n{em_result.get('log_output', '')}")

        # Parse EM results from log
        em_initial_energy = None
        em_final_energy = None
        em_max_force = None
        em_converged = False

        em_log_path = em_result.get("log")
        if em_log_path and os.path.exists(em_log_path):
            with open(em_log_path, 'r') as f:
                em_log = f.read()
                import re
                # Look for "Potential Energy" in the log
                pe_matches = re.findall(r'Potential Energy\s*=\s*([-\d.eE+]+)', em_log)
                if pe_matches:
                    em_initial_energy = float(pe_matches[0])
                    em_final_energy = float(pe_matches[-1])
                # Look for max force
                mf_matches = re.findall(r'Maximum force\s*=\s*([-\d.eE+]+)', em_log)
                if mf_matches:
                    em_max_force = float(mf_matches[-1])
                # Check convergence
                if "converged to Fmax" in em_log:
                    em_converged = True

        async with db_session_factory() as session:
            await update_job(session,
                em_initial_energy=em_initial_energy,
                em_final_energy=em_final_energy,
                em_max_force=em_max_force,
                em_converged=em_converged,
                progress_percent=40.0,
            )

        if not em_converged:
            warnings_list.append(
                "Energy minimization did not fully converge. "
                "This may be acceptable if the maximum force is reasonably low."
            )

        # ══════════════════════════════════════════════════════════════
        # STAGE 6: NVT Equilibration
        # ══════════════════════════════════════════════════════════════
        async with db_session_factory() as session:
            await update_job(session,
                status=JobStatus.EQUILIBRATING_NVT.value,
                current_stage="NVT equilibration",
                progress_percent=45.0,
            )
        await _notify_status(job_id, "running", "nvt", 45, "Running NVT equilibration...")

        nvt_mdp = engine.generate_mdp("nvt", {
            "nvt_steps": config.get("nvt_steps", 50000),
            "dt": config.get("dt", 0.002),
            "temperature": config.get("temperature", 300.0),
            "thermostat": config.get("thermostat", "v-rescale"),
            "constraints": config.get("constraints", "h-bonds"),
            "electrostatics": config.get("electrostatics", "PME"),
            "vdw_cutoff": config.get("vdw_cutoff", 1.0),
            "coulomb_cutoff": config.get("coulomb_cutoff", 1.0),
        })
        nvt_tpr = str(Path(work_dir) / "nvt.tpr")
        em_gro = em_result.get("gro", str(Path(work_dir) / "em.gro"))
        await engine.grompp(nvt_mdp, em_gro, topol, nvt_tpr,
                            maxwarn=2, restraint_file=em_gro)

        nvt_result = await engine.mdrun(nvt_tpr, "nvt")
        log_parts.append(f"=== NVT Equilibration ===\n{nvt_result.get('log_output', '')}")

        # ══════════════════════════════════════════════════════════════
        # STAGE 7: NPT Equilibration
        # ══════════════════════════════════════════════════════════════
        async with db_session_factory() as session:
            await update_job(session,
                status=JobStatus.EQUILIBRATING_NPT.value,
                current_stage="NPT equilibration",
                progress_percent=55.0,
            )
        await _notify_status(job_id, "running", "npt", 55, "Running NPT equilibration...")

        npt_mdp = engine.generate_mdp("npt", {
            "npt_steps": config.get("npt_steps", 50000),
            "dt": config.get("dt", 0.002),
            "temperature": config.get("temperature", 300.0),
            "pressure": config.get("pressure", 1.0),
            "thermostat": config.get("thermostat", "v-rescale"),
            "barostat": config.get("barostat", "Parrinello-Rahman"),
            "constraints": config.get("constraints", "h-bonds"),
            "electrostatics": config.get("electrostatics", "PME"),
            "vdw_cutoff": config.get("vdw_cutoff", 1.0),
            "coulomb_cutoff": config.get("coulomb_cutoff", 1.0),
        })
        npt_tpr = str(Path(work_dir) / "npt.tpr")
        nvt_gro = nvt_result.get("gro", str(Path(work_dir) / "nvt.gro"))
        await engine.grompp(npt_mdp, nvt_gro, topol, npt_tpr,
                            maxwarn=2, restraint_file=em_gro)

        npt_result = await engine.mdrun(npt_tpr, "npt")
        log_parts.append(f"=== NPT Equilibration ===\n{npt_result.get('log_output', '')}")

        # ══════════════════════════════════════════════════════════════
        # STAGE 8: Production MD
        # ══════════════════════════════════════════════════════════════
        async with db_session_factory() as session:
            await update_job(session,
                status=JobStatus.RUNNING_PRODUCTION.value,
                current_stage="Production MD",
                progress_percent=65.0,
            )
        await _notify_status(job_id, "running", "production", 65, "Running production MD...")

        prod_mdp = engine.generate_mdp("prod", {
            "prod_steps": config.get("prod_steps", 500000),
            "dt": config.get("dt", 0.002),
            "temperature": config.get("temperature", 300.0),
            "pressure": config.get("pressure", 1.0),
            "thermostat": config.get("thermostat", "v-rescale"),
            "barostat": config.get("barostat", "Parrinello-Rahman"),
            "constraints": config.get("constraints", "h-bonds"),
            "electrostatics": config.get("electrostatics", "PME"),
            "vdw_cutoff": config.get("vdw_cutoff", 1.0),
            "coulomb_cutoff": config.get("coulomb_cutoff", 1.0),
            "nstxout_compressed": config.get("nstxout_compressed", 5000),
            "nstenergy": config.get("nstenergy", 5000),
        })
        prod_tpr = str(Path(work_dir) / "prod.tpr")
        npt_gro = npt_result.get("gro", str(Path(work_dir) / "npt.gro"))
        await engine.grompp(prod_mdp, npt_gro, topol, prod_tpr, maxwarn=2)

        prod_result = await engine.mdrun(prod_tpr, "prod")
        log_parts.append(f"=== Production MD ===\n{prod_result.get('log_output', '')}")

        # ══════════════════════════════════════════════════════════════
        # STAGE 9: Completed
        # ══════════════════════════════════════════════════════════════
        end_time = datetime.now(timezone.utc)

        final_status = JobStatus.COMPLETED_WITH_WARNINGS.value if warnings_list else JobStatus.COMPLETED.value

        async with db_session_factory() as session:
            await update_job(session,
                status=final_status,
                current_stage="Completed",
                progress_percent=100.0,
                completed_at=end_time,
                warnings=warnings_list,
                log_output="\n\n".join(log_parts[-5:]),  # Keep last 5 stages
            )

        await _notify_status(job_id, final_status, "completed", 100,
                             "Simulation completed successfully!")

    except GromacsError as e:
        logger.error(f"GROMACS error in job {job_id}: {e}")
        async with db_session_factory() as session:
            await update_job(session,
                status=JobStatus.FAILED.value,
                error_message=str(e),
                error_stage=e.command if hasattr(e, 'command') else "unknown",
                log_output="\n\n".join(log_parts),
                warnings=warnings_list,
            )
        await _notify_status(job_id, "failed", "error", 0, str(e))

    except asyncio.CancelledError:
        logger.info(f"Job {job_id} was cancelled")
        async with db_session_factory() as session:
            await update_job(session,
                status=JobStatus.CANCELLED.value,
                log_output="\n\n".join(log_parts),
            )
        await _notify_status(job_id, "cancelled", "cancelled", 0, "Job cancelled by user")

    except Exception as e:
        logger.exception(f"Unexpected error in job {job_id}")
        async with db_session_factory() as session:
            await update_job(session,
                status=JobStatus.FAILED.value,
                error_message=f"Unexpected error: {str(e)}",
                error_stage="unknown",
                log_output="\n\n".join(log_parts),
            )
        await _notify_status(job_id, "failed", "error", 0, f"Unexpected error: {e}")

    finally:
        # Cleanup
        _active_jobs.pop(job_id, None)


def start_simulation(job_id: str, project_id: str, protein_pdb: str,
                      config: dict, db_session_factory,
                      ligand_pdb: Optional[str] = None) -> asyncio.Task:
    """
    Start a simulation as a background async task.
    Returns the asyncio.Task.
    """
    task = asyncio.create_task(
        run_simulation_pipeline(
            job_id=job_id,
            project_id=project_id,
            protein_pdb=protein_pdb,
            config=config,
            db_session_factory=db_session_factory,
            ligand_pdb=ligand_pdb,
        )
    )
    _active_jobs[job_id] = task
    return task


def cancel_simulation(job_id: str) -> bool:
    """Cancel a running simulation."""
    task = _active_jobs.get(job_id)
    if task and not task.done():
        task.cancel()
        return True
    return False


def get_active_job_count() -> int:
    """Return count of currently running jobs."""
    return sum(1 for t in _active_jobs.values() if not t.done())
