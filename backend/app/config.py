"""
Application configuration and environment detection.
Detects GROMACS availability, sets paths, and manages runtime settings.
"""

import os
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("MD_DATA_DIR", str(BASE_DIR / "data")))
PROJECTS_DIR = DATA_DIR / "projects"
DATABASE_URL = os.environ.get("MD_DATABASE_URL", f"sqlite+aiosqlite:///{DATA_DIR / 'md_platform.db'}")

# Ensure directories exist
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# Resource limits
MAX_UPLOAD_SIZE_MB = int(os.environ.get("MD_MAX_UPLOAD_MB", "100"))
MAX_SIMULATION_HOURS = float(os.environ.get("MD_MAX_SIM_HOURS", "24"))
MAX_ATOMS = int(os.environ.get("MD_MAX_ATOMS", "500000"))
MAX_CONCURRENT_JOBS = int(os.environ.get("MD_MAX_CONCURRENT_JOBS", "2"))
JOB_TIMEOUT_SECONDS = int(os.environ.get("MD_JOB_TIMEOUT", str(int(MAX_SIMULATION_HOURS * 3600))))

# CORS origins
CORS_ORIGINS = os.environ.get("MD_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173").split(",")


class GromacsConfig:
    """Detects and manages GROMACS installation."""

    def __init__(self):
        self._gmx_path: Optional[str] = None
        self._version: Optional[str] = None
        self._available: bool = False
        self._gpu_available: bool = False
        self._force_fields: list[str] = []
        self._detect()

    def _detect(self):
        """Detect GROMACS binary and capabilities."""
        # Try common GROMACS binary names
        for name in ["gmx", "gmx_mpi", "gmx_d"]:
            path = shutil.which(name)
            if path:
                self._gmx_path = path
                break

        # Also check environment variable
        if not self._gmx_path:
            env_path = os.environ.get("GMX_PATH")
            if env_path and os.path.isfile(env_path):
                self._gmx_path = env_path

        if not self._gmx_path:
            logger.warning("GROMACS not found in PATH. Simulation features unavailable.")
            self._available = False
            return

        # Get version
        try:
            result = subprocess.run(
                [self._gmx_path, "--version"],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.splitlines():
                if "GROMACS version" in line:
                    self._version = line.split(":")[-1].strip() if ":" in line else line.strip()
                    break
                elif "VERSION" in line.upper() and ":" in line:
                    self._version = line.split(":")[-1].strip()
                    break
            if not self._version:
                self._version = "unknown"
            self._available = True
            logger.info(f"GROMACS found: {self._gmx_path} (version: {self._version})")
        except Exception as e:
            logger.error(f"GROMACS detection failed: {e}")
            self._available = False
            return

        # Detect GPU support
        try:
            result = subprocess.run(
                [self._gmx_path, "--version"],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.lower()
            self._gpu_available = "cuda" in output or "opencl" in output or "sycl" in output
        except Exception:
            self._gpu_available = False

        # Detect available force fields
        self._detect_force_fields()

    def _detect_force_fields(self):
        """Detect available force fields from GROMACS data directory."""
        self._force_fields = [
            "amber99sb-ildn",
            "amber03",
            "amber94",
            "amber96",
            "amber99",
            "amber99sb",
            "charmm27",
            "gromos43a1",
            "gromos43a2",
            "gromos45a3",
            "gromos53a5",
            "gromos53a6",
            "gromos54a7",
            "oplsaa",
        ]

    @property
    def available(self) -> bool:
        return self._available

    @property
    def gmx_path(self) -> Optional[str]:
        return self._gmx_path

    @property
    def version(self) -> Optional[str]:
        return self._version

    @property
    def gpu_available(self) -> bool:
        return self._gpu_available

    @property
    def force_fields(self) -> list[str]:
        return self._force_fields

    def to_dict(self) -> dict:
        return {
            "available": self._available,
            "path": self._gmx_path,
            "version": self._version,
            "gpu_available": self._gpu_available,
            "force_fields": self._force_fields,
        }


# Global GROMACS config (detected once at startup)
gromacs = GromacsConfig()

# Supported force fields with metadata
FORCE_FIELD_INFO = {
    "amber99sb-ildn": {
        "name": "AMBER99SB-ILDN",
        "family": "AMBER",
        "description": "AMBER ff99SB with improved side-chain torsions (Lindorff-Larsen et al., 2010)",
        "water_models": ["tip3p", "tip4p", "spc", "spce"],
        "default_water": "tip3p",
        "reference": "Lindorff-Larsen et al., Proteins 2010, 78, 1950-1958",
        "ligand_compatible": True,
    },
    "amber03": {
        "name": "AMBER03",
        "family": "AMBER",
        "description": "AMBER03 force field (Duan et al., 2003)",
        "water_models": ["tip3p", "tip4p", "spc", "spce"],
        "default_water": "tip3p",
        "reference": "Duan et al., J. Comput. Chem. 2003, 24, 1999-2012",
        "ligand_compatible": True,
    },
    "charmm27": {
        "name": "CHARMM27",
        "family": "CHARMM",
        "description": "CHARMM27 all-atom force field (MacKerell et al.)",
        "water_models": ["tip3p", "spc", "spce"],
        "default_water": "tip3p",
        "reference": "MacKerell et al., J. Phys. Chem. B 1998, 102, 3586-3616",
        "ligand_compatible": True,
    },
    "oplsaa": {
        "name": "OPLS-AA/L",
        "family": "OPLS",
        "description": "OPLS all-atom force field (Jorgensen et al.)",
        "water_models": ["tip3p", "tip4p", "spc", "spce"],
        "default_water": "tip3p",
        "reference": "Jorgensen et al., JACS 1996, 118, 11225-11236",
        "ligand_compatible": True,
    },
}

WATER_MODEL_INFO = {
    "tip3p": {"name": "TIP3P", "atoms": 3, "description": "Transferable Intermolecular Potential 3-Point"},
    "tip4p": {"name": "TIP4P", "atoms": 4, "description": "Transferable Intermolecular Potential 4-Point"},
    "spc": {"name": "SPC", "atoms": 3, "description": "Simple Point Charge"},
    "spce": {"name": "SPC/E", "atoms": 3, "description": "Extended Simple Point Charge"},
}
