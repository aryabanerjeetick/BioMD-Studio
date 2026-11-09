import pytest
import os
import tempfile
import numpy as np
import mdtraj as md
from app.services.analysis_engine import (
    compute_rmsd,
    compute_rmsf,
    compute_radius_of_gyration,
    compute_sasa,
    compute_hbonds,
    compute_pca,
    compute_contact_map,
    compute_secondary_structure,
)
from test_backend import SAMPLE_PDB_CONTENT

def create_mock_real_trajectory():
    """Create a real MDTraj Trajectory object with 5 distinct frames for testing."""
    with tempfile.NamedTemporaryFile("w", suffix=".pdb", delete=False) as f:
        f.write(SAMPLE_PDB_CONTENT)
        pdb_path = f.name
    try:
        base_traj = md.load(pdb_path)
        # Create 5 frames with small realistic thermal fluctuations
        xyz = np.repeat(base_traj.xyz, 5, axis=0)
        np.random.seed(42)
        xyz += np.random.normal(0, 0.02, size=xyz.shape) # 0.2 Å fluctuation
        traj = md.Trajectory(xyz, base_traj.topology)
        traj.time = np.array([0.0, 10.0, 20.0, 30.0, 40.0]) # ps
        return traj
    finally:
        if os.path.exists(pdb_path):
            os.remove(pdb_path)

def test_rmsd_calculation():
    traj = create_mock_real_trajectory()
    res = compute_rmsd(traj, atom_selection="backbone")
    assert res["status"] == "completed"
    assert len(res["data"]["time_ps"]) == 5
    assert len(res["data"]["rmsd_nm"]) == 5
    # First frame against itself has RMSD = 0
    assert abs(res["data"]["rmsd_nm"][0]) < 1e-4
    assert res["data"]["mean_rmsd_nm"] > 0
    assert res["metadata"]["atom_selection"] == "Backbone"

def test_rmsf_calculation():
    traj = create_mock_real_trajectory()
    res = compute_rmsf(traj, atom_selection="name CA")
    assert res["status"] == "completed"
    assert len(res["data"]["rmsf_nm"]) == 3  # 3 residues CA
    assert len(res["data"]["residue_labels"]) == 3
    assert res["data"]["mean_rmsf_nm"] > 0

def test_radius_of_gyration():
    traj = create_mock_real_trajectory()
    res = compute_radius_of_gyration(traj)
    assert res["status"] == "completed"
    assert len(res["data"]["rg_nm"]) == 5
    assert res["data"]["mean_rg_nm"] > 0

def test_sasa_calculation():
    traj = create_mock_real_trajectory()
    res = compute_sasa(traj, mode="both")
    assert res["status"] == "completed"
    assert len(res["data"]["total_sasa_nm2"]) == 5
    assert "per_residue_sasa_nm2" in res["data"]
    assert res["data"]["mean_sasa_nm2"] > 0

def test_pca_calculation():
    traj = create_mock_real_trajectory()
    res = compute_pca(traj, atom_selection="name CA", n_components=3)
    assert res["status"] == "completed"
    assert len(res["data"]["projections_pc1"]) == 5
    assert len(res["data"]["explained_variance_pct"]) <= 3

def test_contact_map():
    traj = create_mock_real_trajectory()
    res = compute_contact_map(traj, cutoff=0.5)
    assert res["status"] == "completed"
    assert len(res["data"]["contact_matrix"]) == traj.topology.n_residues
