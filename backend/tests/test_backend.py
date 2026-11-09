import pytest
from httpx import AsyncClient, ASGITransport
import os
import tempfile
from app.main import app
from app.database import init_db
from app.utils.file_utils import safe_filename, compute_checksum
from app.services.structure_validator import validate_protein_structure, detect_file_type

# Sample minimal PDB (Alanine dipeptide / Ala3 peptide)
SAMPLE_PDB_CONTENT = """HEADER    PEPTIDE TEST                             01-JAN-24   1XYZ
CRYST1   50.000   50.000   50.000  90.00  90.00  90.00 P 1           1
ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00 20.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00 20.00           C
ATOM      3  C   ALA A   1       2.009   1.425   0.000  1.00 20.00           C
ATOM      4  O   ALA A   1       1.246   2.392   0.000  1.00 20.00           O
ATOM      5  CB  ALA A   1       1.986  -0.767  -1.218  1.00 20.00           C
ATOM      6  N   ALA A   2       3.332   1.545   0.000  1.00 20.00           N
ATOM      7  CA  ALA A   2       4.004   2.846   0.000  1.00 20.00           C
ATOM      8  C   ALA A   2       5.513   2.665   0.000  1.00 20.00           C
ATOM      9  O   ALA A   2       6.275   3.632   0.000  1.00 20.00           O
ATOM     10  CB  ALA A   2       3.532   3.613  -1.218  1.00 20.00           C
ATOM     11  N   ALA A   3       5.923   1.398   0.000  1.00 20.00           N
ATOM     12  CA  ALA A   3       7.348   1.085   0.000  1.00 20.00           C
ATOM     13  C   ALA A   3       7.534  -0.424   0.000  1.00 20.00           C
ATOM     14  O   ALA A   3       8.665  -0.899   0.000  1.00 20.00           O
ATOM     15  CB  ALA A   3       8.095   1.716  -1.182  1.00 20.00           C
TER      16      ALA A   3
HETATM   17  O   HOH A   4       0.000   5.000   5.000  1.00 30.00           O
END
"""

@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "scientific_integrity" in data
    assert data["gromacs_available"] is False  # On this machine GROMACS is honestly detected as not installed

@pytest.mark.asyncio
async def test_project_crud():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create
        create_res = await ac.post("/api/projects", json={
            "name": "Kinase Inhibitor MD",
            "description": "Simulation of EGFR with erlotinib",
            "simulation_type": "protein_ligand",
            "scientific_objective": "Test stability of ligand pose"
        })
        assert create_res.status_code == 200
        project = create_res.json()
        assert project["name"] == "Kinase Inhibitor MD"
        project_id = project["id"]

        # List
        list_res = await ac.get("/api/projects")
        assert list_res.status_code == 200
        projects = list_res.json()
        assert any(p["id"] == project_id for p in projects)

        # Get
        get_res = await ac.get(f"/api/projects/{project_id}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "Kinase Inhibitor MD"

        # Delete
        del_res = await ac.delete(f"/api/projects/{project_id}")
        assert del_res.status_code == 200

def test_safe_filename():
    assert safe_filename("test/file\\name..pdb") == "test_file_name.pdb"
    assert safe_filename("valid_name.gro") == "valid_name.gro"

def test_structure_validation_pdb():
    with tempfile.NamedTemporaryFile("w", suffix=".pdb", delete=False) as f:
        f.write(SAMPLE_PDB_CONTENT)
        temp_path = f.name

    try:
        assert detect_file_type(temp_path) == "pdb"
        report = validate_protein_structure(temp_path)
        assert report["is_valid"] is True
        assert report["n_atoms"] == 16  # 15 protein + 1 water
        assert report["n_residues"] == 4  # 3 amino acids + 1 water
        assert report["chains"][0]["n_protein_residues"] == 3
        assert report["n_chains"] == 1
        assert report["has_waters"] is True
        assert report["n_waters"] == 1
        assert "A" in report["sequence"]
        assert report["sequence"]["A"] == "AAA"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_simulation_system_status():
    transport = ASGITransport(app=app)
    import asyncio
    async def run():
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/simulation/system-status")
            assert res.status_code == 200
            data = res.json()
            assert "gromacs" in data
            assert "amber99sb-ildn" in data["force_fields"]
            assert "tip3p" in data["water_models"]
    asyncio.run(run())
