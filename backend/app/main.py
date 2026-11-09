"""
MD Simulation Platform — FastAPI Main Application
==================================================
A genuine molecular dynamics simulation platform.
All results come from real computations — nothing is fabricated.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

from .config import CORS_ORIGINS, gromacs, DATA_DIR
from .database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize database on startup."""
    logger.info("=== MD Simulation Platform Starting ===")
    await init_db()
    logger.info(f"Database initialized at: {DATA_DIR}")
    logger.info(f"GROMACS available: {gromacs.available}")
    if gromacs.available:
        logger.info(f"GROMACS version: {gromacs.version}")
        logger.info(f"GROMACS GPU: {gromacs.gpu_available}")
    else:
        logger.warning(
            "GROMACS is NOT installed. Simulation features will be unavailable. "
            "Analysis of uploaded trajectories is still available."
        )
    yield
    logger.info("=== MD Simulation Platform Shutting Down ===")


app = FastAPI(
    title="MD Simulation Platform",
    description=(
        "A genuine molecular dynamics simulation platform for research. "
        "All reported results come from actual computations — "
        "this platform never fabricates scientific data."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],  # Allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers
from .routers import projects, structures, simulation, analysis, files, ws

app.include_router(projects.router)
app.include_router(structures.router)
app.include_router(simulation.router)
app.include_router(analysis.router)
app.include_router(files.router)
app.include_router(ws.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    from .services.analysis_engine import MDTRAJ_AVAILABLE, MDTRAJ_VERSION
    return {
        "status": "healthy",
        "platform": "MD Simulation Platform",
        "version": "1.0.0",
        "gromacs_available": gromacs.available,
        "gromacs_version": gromacs.version,
        "mdtraj_available": MDTRAJ_AVAILABLE,
        "mdtraj_version": MDTRAJ_VERSION,
        "scientific_integrity": (
            "All results are computed from actual data. "
            "No values are fabricated or pre-loaded."
        ),
    }


# Serve frontend static files if they exist
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
