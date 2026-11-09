"""
SQLAlchemy database models and session management.
Uses SQLite for local/development, supports PostgreSQL for production.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Boolean, JSON,
    ForeignKey, Enum as SAEnum, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker as async_sessionmaker
import enum
import uuid

from .config import DATABASE_URL

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


class JobStatus(str, enum.Enum):
    CREATED = "created"
    VALIDATING = "validating"
    PREPARING_PROTEIN = "preparing_protein"
    PREPARING_LIGAND = "preparing_ligand"
    BUILDING_SYSTEM = "building_system"
    MINIMIZING = "minimizing"
    EQUILIBRATING_NVT = "equilibrating_nvt"
    EQUILIBRATING_NPT = "equilibrating_npt"
    RUNNING_PRODUCTION = "running_production"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimulationType(str, enum.Enum):
    PROTEIN_ONLY = "protein_only"
    PROTEIN_LIGAND = "protein_ligand"
    NUCLEIC_ACID = "nucleic_acid"


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    simulation_type = Column(String(50), default=SimulationType.PROTEIN_LIGAND.value)
    scientific_objective = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    jobs = relationship("SimulationJob", back_populates="project", cascade="all, delete-orphan")


class ProjectFile(Base):
    __tablename__ = "project_files"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50))  # pdb, cif, sdf, mol2, gro, xtc, etc.
    file_role = Column(String(50))  # protein, ligand, complex, trajectory, topology, etc.
    file_size = Column(Integer)
    checksum = Column(String(64))  # SHA-256
    disk_path = Column(String(1024), nullable=False)
    validation_status = Column(String(50), default="pending")
    validation_report = Column(JSON, default=dict)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="files")


class SimulationJob(Base):
    __tablename__ = "simulation_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    status = Column(String(50), default=JobStatus.CREATED.value)
    current_stage = Column(String(100), default="")
    progress_percent = Column(Float, default=0.0)

    # Configuration
    force_field = Column(String(50), default="amber99sb-ildn")
    water_model = Column(String(50), default="tip3p")
    box_type = Column(String(50), default="dodecahedron")
    box_distance = Column(Float, default=1.0)  # nm
    salt_concentration = Column(Float, default=0.15)  # M
    cation = Column(String(10), default="NA")
    anion = Column(String(10), default="CL")

    # Minimization parameters
    em_steps = Column(Integer, default=50000)
    em_tol = Column(Float, default=1000.0)  # kJ/mol/nm

    # Equilibration parameters
    nvt_steps = Column(Integer, default=50000)
    npt_steps = Column(Integer, default=50000)
    eq_temperature = Column(Float, default=300.0)  # K
    eq_pressure = Column(Float, default=1.0)  # bar
    eq_dt = Column(Float, default=0.002)  # ps

    # Production parameters
    prod_steps = Column(Integer, default=500000)
    prod_dt = Column(Float, default=0.002)  # ps
    prod_temperature = Column(Float, default=300.0)
    prod_pressure = Column(Float, default=1.0)
    nstxout_compressed = Column(Integer, default=5000)
    nstenergy = Column(Integer, default=5000)
    nstlog = Column(Integer, default=5000)

    # Thermostat / Barostat
    thermostat = Column(String(50), default="v-rescale")
    barostat = Column(String(50), default="Parrinello-Rahman")
    constraints = Column(String(50), default="h-bonds")
    electrostatics = Column(String(50), default="PME")
    vdw_cutoff = Column(Float, default=1.0)  # nm
    coulomb_cutoff = Column(Float, default=1.0)  # nm

    # System info (populated after setup)
    n_protein_atoms = Column(Integer, default=0)
    n_ligand_atoms = Column(Integer, default=0)
    n_water_molecules = Column(Integer, default=0)
    n_ions = Column(Integer, default=0)
    n_total_atoms = Column(Integer, default=0)
    system_charge = Column(Float, default=0.0)

    # Execution info
    work_dir = Column(String(1024), default="")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    elapsed_seconds = Column(Float)
    error_message = Column(Text, default="")
    error_stage = Column(String(100), default="")
    warnings = Column(JSON, default=list)
    log_output = Column(Text, default="")

    # Results (populated after analysis)
    em_initial_energy = Column(Float)
    em_final_energy = Column(Float)
    em_max_force = Column(Float)
    em_converged = Column(Boolean)

    # Analysis results stored as JSON
    analysis_results = Column(JSON, default=dict)

    # Provenance
    gromacs_version = Column(String(100), default="")
    random_seed = Column(Integer, default=-1)
    input_checksums = Column(JSON, default=dict)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="jobs")


# Async engine and session
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency for FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
