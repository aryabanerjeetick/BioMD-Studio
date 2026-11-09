"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


# ── Project Schemas ──────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    simulation_type: str = "protein_ligand"
    scientific_objective: str = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    simulation_type: Optional[str] = None
    scientific_objective: Optional[str] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    simulation_type: str
    scientific_objective: str
    created_at: datetime
    updated_at: datetime
    file_count: int = 0
    job_count: int = 0


# ── File Schemas ─────────────────────────────────────────────────────────

class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    original_filename: str
    file_type: Optional[str]
    file_role: Optional[str]
    file_size: Optional[int]
    checksum: Optional[str]
    validation_status: str
    validation_report: dict
    uploaded_at: datetime


# ── Structure Validation Schemas ─────────────────────────────────────────

class StructureValidationReport(BaseModel):
    """Detailed structure validation results."""
    is_valid: bool = False
    file_type: str = ""
    n_models: int = 0
    n_chains: int = 0
    n_residues: int = 0
    n_atoms: int = 0
    chains: list[dict] = []
    missing_residues: list[dict] = []
    missing_atoms: list[dict] = []
    nonstandard_residues: list[dict] = []
    disulfide_bonds: list[dict] = []
    alternate_conformations: list[dict] = []
    has_waters: bool = False
    n_waters: int = 0
    has_ligands: bool = False
    ligands: list[dict] = []
    has_metals: bool = False
    metals: list[dict] = []
    has_nucleic_acids: bool = False
    warnings: list[str] = []
    errors: list[str] = []
    sequence: dict = {}  # chain_id -> sequence string


class LigandValidationReport(BaseModel):
    """Ligand-specific validation results."""
    is_valid: bool = False
    name: str = ""
    formula: str = ""
    molecular_weight: float = 0.0
    n_atoms: int = 0
    n_heavy_atoms: int = 0
    n_bonds: int = 0
    formal_charge: int = 0
    has_3d_coords: bool = False
    has_hydrogens: bool = False
    n_hydrogens: int = 0
    warnings: list[str] = []
    errors: list[str] = []


# ── Simulation Configuration Schemas ─────────────────────────────────────

class SimulationConfig(BaseModel):
    """Full simulation configuration."""
    # Force field
    force_field: str = "amber99sb-ildn"
    water_model: str = "tip3p"

    # Box
    box_type: str = "dodecahedron"
    box_distance: float = Field(1.0, ge=0.5, le=5.0)

    # Ions
    salt_concentration: float = Field(0.15, ge=0.0, le=2.0)
    cation: str = "NA"
    anion: str = "CL"

    # Energy minimization
    em_steps: int = Field(50000, ge=1000, le=500000)
    em_tol: float = Field(1000.0, ge=1.0, le=10000.0)

    # NVT equilibration
    nvt_steps: int = Field(50000, ge=1000, le=500000)

    # NPT equilibration
    npt_steps: int = Field(50000, ge=1000, le=500000)

    # Temperature and pressure
    temperature: float = Field(300.0, ge=200.0, le=500.0)
    pressure: float = Field(1.0, ge=0.1, le=100.0)
    dt: float = Field(0.002, ge=0.0005, le=0.004)

    # Production
    prod_steps: int = Field(500000, ge=10000, le=500000000)
    nstxout_compressed: int = Field(5000, ge=100, le=100000)
    nstenergy: int = Field(5000, ge=100, le=100000)

    # Methods
    thermostat: str = "v-rescale"
    barostat: str = "Parrinello-Rahman"
    constraints: str = "h-bonds"
    electrostatics: str = "PME"
    vdw_cutoff: float = Field(1.0, ge=0.8, le=2.0)
    coulomb_cutoff: float = Field(1.0, ge=0.8, le=2.0)


# ── Job Schemas ──────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    status: str
    current_stage: str
    progress_percent: float
    force_field: str
    water_model: str
    n_total_atoms: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    elapsed_seconds: Optional[float]
    error_message: str
    error_stage: str
    warnings: list
    gromacs_version: str
    em_initial_energy: Optional[float]
    em_final_energy: Optional[float]
    em_converged: Optional[bool]
    created_at: datetime


class JobStatusUpdate(BaseModel):
    """WebSocket job status update message."""
    job_id: str
    status: str
    stage: str
    progress: float
    message: str
    timestamp: str


# ── Analysis Schemas ─────────────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    """Request a specific analysis."""
    analysis_type: str  # rmsd, rmsf, rg, energy, hbonds, sasa, pca, etc.
    parameters: dict = {}  # Analysis-specific parameters


class AnalysisResult(BaseModel):
    """Analysis result with data and metadata."""
    analysis_type: str
    status: str  # completed, failed, not_available
    data: dict = {}  # The actual numerical data
    metadata: dict = {}  # Parameters, frame count, time range, etc.
    warnings: list[str] = []
    error: Optional[str] = None


# ── System Status ────────────────────────────────────────────────────────

class SystemStatus(BaseModel):
    gromacs_available: bool
    gromacs_version: Optional[str]
    gromacs_gpu: bool
    mdtraj_available: bool
    max_upload_mb: int
    max_atoms: int
    max_simulation_hours: float
    max_concurrent_jobs: int
    active_jobs: int = 0
