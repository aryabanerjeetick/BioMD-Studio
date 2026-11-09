"""
Structures API router — upload, validate, and manage molecular structure files.
"""

import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from ..database import get_db, Project, ProjectFile
from ..models import FileResponse, StructureValidationReport
from ..services.structure_validator import (
    validate_protein_structure,
    detect_file_type,
    compute_file_checksum,
    extract_protein_pdb,
    extract_ligand_from_pdb,
)
from ..config import PROJECTS_DIR, MAX_UPLOAD_SIZE_MB
from ..utils.file_utils import safe_filename

router = APIRouter(prefix="/api/structures", tags=["structures"])


@router.post("/upload/{project_id}", response_model=FileResponse)
async def upload_structure(
    project_id: str,
    file: UploadFile = File(...),
    file_role: str = Form("auto"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a molecular structure file (PDB, CIF, SDF, MOL2, GRO).
    Validates the file content and stores it.
    """
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check file size
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum: {MAX_UPLOAD_SIZE_MB} MB"
        )

    # Save file
    project_dir = PROJECTS_DIR / project_id / "uploads"
    project_dir.mkdir(parents=True, exist_ok=True)

    safe_name = safe_filename(file.filename or "structure")
    file_id = str(uuid.uuid4())
    # Preserve extension
    _, ext = os.path.splitext(safe_name)
    stored_name = f"{file_id}{ext}"
    file_path = project_dir / stored_name

    with open(file_path, 'wb') as f:
        f.write(contents)

    # Detect file type from content
    file_type = detect_file_type(str(file_path))

    # Compute checksum
    checksum = compute_file_checksum(str(file_path))

    # Auto-detect role
    if file_role == "auto":
        if file_type in ("pdb", "cif"):
            file_role = "complex"  # Could be protein or complex
        elif file_type in ("sdf", "mol2"):
            file_role = "ligand"
        elif file_type == "gro":
            file_role = "structure"
        else:
            file_role = "unknown"

    # Create database record
    db_file = ProjectFile(
        id=file_id,
        project_id=project_id,
        filename=stored_name,
        original_filename=file.filename or "structure",
        file_type=file_type,
        file_role=file_role,
        file_size=len(contents),
        checksum=checksum,
        disk_path=str(file_path),
        validation_status="pending",
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)

    return FileResponse(
        id=db_file.id,
        filename=db_file.filename,
        original_filename=db_file.original_filename,
        file_type=db_file.file_type,
        file_role=db_file.file_role,
        file_size=db_file.file_size,
        checksum=db_file.checksum,
        validation_status=db_file.validation_status,
        validation_report=db_file.validation_report or {},
        uploaded_at=db_file.uploaded_at,
    )


@router.post("/validate/{file_id}")
async def validate_structure(file_id: str, db: AsyncSession = Depends(get_db)):
    """
    Validate an uploaded structure file.
    Returns a detailed validation report based on actual file content.
    """
    result = await db.execute(select(ProjectFile).where(ProjectFile.id == file_id))
    db_file = result.scalar_one_or_none()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.exists(db_file.disk_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    file_type = db_file.file_type or detect_file_type(db_file.disk_path)

    if file_type in ("pdb", "cif"):
        report = validate_protein_structure(db_file.disk_path)
    else:
        report = {
            "is_valid": True,
            "file_type": file_type,
            "warnings": [],
            "errors": [],
            "n_atoms": 0,
            "n_residues": 0,
            "n_chains": 0,
        }

    # Update database
    db_file.validation_status = "valid" if report.get("is_valid") else "invalid"
    db_file.validation_report = report
    db_file.file_type = file_type
    await db.commit()

    return report


@router.get("/files/{project_id}", response_model=list[FileResponse])
async def list_files(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all files for a project."""
    result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.uploaded_at.desc())
    )
    files = result.scalars().all()

    return [FileResponse(
        id=f.id,
        filename=f.filename,
        original_filename=f.original_filename,
        file_type=f.file_type,
        file_role=f.file_role,
        file_size=f.file_size,
        checksum=f.checksum,
        validation_status=f.validation_status,
        validation_report=f.validation_report or {},
        uploaded_at=f.uploaded_at,
    ) for f in files]


@router.post("/extract-protein/{file_id}")
async def extract_protein(
    file_id: str,
    keep_waters: bool = False,
    keep_ligands: bool = False,
    chains: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Extract protein from a complex structure."""
    result = await db.execute(select(ProjectFile).where(ProjectFile.id == file_id))
    db_file = result.scalar_one_or_none()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    project_dir = PROJECTS_DIR / db_file.project_id / "prepared"
    project_dir.mkdir(parents=True, exist_ok=True)

    output_path = str(project_dir / "protein_clean.pdb")
    chain_list = chains.split(",") if chains else None

    extraction = extract_protein_pdb(
        db_file.disk_path, output_path,
        keep_waters=keep_waters,
        keep_ligands=keep_ligands,
        chains=chain_list,
    )

    if not extraction["success"]:
        raise HTTPException(status_code=400, detail=extraction.get("error", "Extraction failed"))

    # Save as new file
    new_file = ProjectFile(
        project_id=db_file.project_id,
        filename="protein_clean.pdb",
        original_filename="protein_clean.pdb",
        file_type="pdb",
        file_role="protein",
        file_size=os.path.getsize(output_path),
        checksum=compute_file_checksum(output_path),
        disk_path=output_path,
        validation_status="valid",
    )
    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)

    return {**extraction, "file_id": new_file.id}


@router.post("/extract-ligand/{file_id}")
async def extract_ligand(
    file_id: str,
    ligand_name: str,
    chain_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Extract a ligand from a complex structure."""
    result = await db.execute(select(ProjectFile).where(ProjectFile.id == file_id))
    db_file = result.scalar_one_or_none()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    project_dir = PROJECTS_DIR / db_file.project_id / "prepared"
    project_dir.mkdir(parents=True, exist_ok=True)

    output_path = str(project_dir / f"ligand_{ligand_name}.pdb")

    extraction = extract_ligand_from_pdb(
        db_file.disk_path, ligand_name, output_path, chain_id=chain_id
    )

    if not extraction["success"]:
        raise HTTPException(status_code=400, detail=extraction.get("error", "Extraction failed"))

    new_file = ProjectFile(
        project_id=db_file.project_id,
        filename=f"ligand_{ligand_name}.pdb",
        original_filename=f"ligand_{ligand_name}.pdb",
        file_type="pdb",
        file_role="ligand",
        file_size=os.path.getsize(output_path),
        checksum=compute_file_checksum(output_path),
        disk_path=output_path,
        validation_status="valid",
    )
    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)

    return {**extraction, "file_id": new_file.id}


@router.get("/content/{file_id}")
async def get_file_content(file_id: str, db: AsyncSession = Depends(get_db)):
    """Get the raw content of a structure file (for NGL viewer)."""
    result = await db.execute(select(ProjectFile).where(ProjectFile.id == file_id))
    db_file = result.scalar_one_or_none()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.exists(db_file.disk_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    from fastapi.responses import FileResponse as FastAPIFileResponse
    return FastAPIFileResponse(
        db_file.disk_path,
        media_type="text/plain",
        filename=db_file.original_filename,
    )
