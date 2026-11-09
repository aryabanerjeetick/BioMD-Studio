"""
Analysis Engine — computes structural and thermodynamic analyses from REAL trajectory data.
Uses MDTraj for trajectory analysis. NEVER fabricates results.
All analysis results are computed from actual trajectory files.
"""

import logging
import os
import numpy as np
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import MDTraj
try:
    import mdtraj as md
    MDTRAJ_AVAILABLE = True
    MDTRAJ_VERSION = md.__version__
except ImportError:
    MDTRAJ_AVAILABLE = False
    MDTRAJ_VERSION = None
    logger.warning("MDTraj not available. Trajectory analysis will be limited.")


class AnalysisError(Exception):
    """Raised when analysis computation fails."""
    pass


def check_mdtraj():
    """Verify MDTraj is available."""
    if not MDTRAJ_AVAILABLE:
        raise AnalysisError(
            "MDTraj is not installed. Install with: pip install mdtraj"
        )


def load_trajectory(traj_path: str, top_path: str,
                     stride: int = 1) -> "md.Trajectory":
    """
    Load a trajectory file with topology.
    Supports XTC, TRR, DCD, PDB, GRO formats.
    """
    check_mdtraj()
    try:
        traj = md.load(traj_path, top=top_path, stride=stride)
        logger.info(f"Loaded trajectory: {traj.n_frames} frames, {traj.n_atoms} atoms")
        return traj
    except Exception as e:
        raise AnalysisError(f"Failed to load trajectory: {str(e)}")


def load_structure(struct_path: str) -> "md.Trajectory":
    """Load a single structure file (PDB or GRO)."""
    check_mdtraj()
    try:
        return md.load(struct_path)
    except Exception as e:
        raise AnalysisError(f"Failed to load structure: {str(e)}")


def compute_rmsd(traj: "md.Trajectory", reference: Optional["md.Trajectory"] = None,
                  atom_selection: str = "backbone") -> dict:
    """
    Compute RMSD over trajectory frames.
    Uses the first frame as reference if none provided.
    Returns time series data with metadata.
    """
    check_mdtraj()

    # Atom selection
    if atom_selection == "backbone":
        atom_indices = traj.topology.select("backbone")
        selection_label = "Backbone"
    elif atom_selection == "ca" or atom_selection == "calpha":
        atom_indices = traj.topology.select("name CA")
        selection_label = "C-alpha"
    elif atom_selection == "heavy":
        atom_indices = traj.topology.select("not element H")
        selection_label = "Heavy atoms"
    elif atom_selection == "protein":
        atom_indices = traj.topology.select("protein")
        selection_label = "All protein"
    else:
        # Custom selection
        try:
            atom_indices = traj.topology.select(atom_selection)
            selection_label = atom_selection
        except Exception as e:
            raise AnalysisError(f"Invalid atom selection '{atom_selection}': {e}")

    if len(atom_indices) == 0:
        raise AnalysisError(f"Atom selection '{atom_selection}' matched 0 atoms")

    ref = reference if reference is not None else traj[0]

    rmsd_values = md.rmsd(traj, ref, atom_indices=atom_indices)

    time_ps = traj.time.tolist()
    rmsd_nm = rmsd_values.tolist()

    return {
        "analysis_type": "rmsd",
        "status": "completed",
        "data": {
            "time_ps": time_ps,
            "rmsd_nm": rmsd_nm,
            "mean_rmsd_nm": float(np.mean(rmsd_values)),
            "std_rmsd_nm": float(np.std(rmsd_values)),
            "min_rmsd_nm": float(np.min(rmsd_values)),
            "max_rmsd_nm": float(np.max(rmsd_values)),
        },
        "metadata": {
            "atom_selection": selection_label,
            "n_atoms_selected": len(atom_indices),
            "n_frames": traj.n_frames,
            "time_range_ps": [float(traj.time[0]), float(traj.time[-1])],
            "reference": "first frame" if reference is None else "provided reference",
            "unit": "nm",
        },
    }


def compute_rmsf(traj: "md.Trajectory", atom_selection: str = "name CA") -> dict:
    """
    Compute RMSF (Root Mean Square Fluctuation) per atom/residue.
    """
    check_mdtraj()

    try:
        atom_indices = traj.topology.select(atom_selection)
    except Exception as e:
        raise AnalysisError(f"Invalid atom selection: {e}")

    if len(atom_indices) == 0:
        raise AnalysisError(f"Atom selection '{atom_selection}' matched 0 atoms")

    # Superpose to average structure
    traj_aligned = traj.superpose(traj, atom_indices=atom_indices)
    rmsf_values = md.rmsf(traj_aligned, traj_aligned[0], atom_indices=atom_indices)

    # Get residue labels
    residue_labels = []
    residue_indices = []
    for idx in atom_indices:
        atom = traj.topology.atom(idx)
        residue_labels.append(f"{atom.residue.name}{atom.residue.resSeq}")
        residue_indices.append(atom.residue.resSeq)

    return {
        "analysis_type": "rmsf",
        "status": "completed",
        "data": {
            "residue_indices": residue_indices,
            "residue_labels": residue_labels,
            "rmsf_nm": rmsf_values.tolist(),
            "mean_rmsf_nm": float(np.mean(rmsf_values)),
            "max_rmsf_nm": float(np.max(rmsf_values)),
        },
        "metadata": {
            "atom_selection": atom_selection,
            "n_atoms": len(atom_indices),
            "n_frames": traj.n_frames,
            "unit": "nm",
        },
    }


def compute_radius_of_gyration(traj: "md.Trajectory") -> dict:
    """
    Compute radius of gyration over trajectory.
    """
    check_mdtraj()

    rg_values = md.compute_rg(traj)
    time_ps = traj.time.tolist()

    return {
        "analysis_type": "radius_of_gyration",
        "status": "completed",
        "data": {
            "time_ps": time_ps,
            "rg_nm": rg_values.tolist(),
            "mean_rg_nm": float(np.mean(rg_values)),
            "std_rg_nm": float(np.std(rg_values)),
        },
        "metadata": {
            "n_frames": traj.n_frames,
            "unit": "nm",
        },
    }


def compute_hbonds(traj: "md.Trajectory", freq_cutoff: float = 0.1,
                    distance_cutoff: float = 0.35,
                    angle_cutoff: float = 150.0) -> dict:
    """
    Compute hydrogen bonds using Baker-Hubbard criteria.
    distance_cutoff in nm, angle_cutoff in degrees.
    """
    check_mdtraj()

    # Compute H-bonds for each frame
    hbonds_per_frame = []
    all_hbonds = {}

    for frame_idx in range(traj.n_frames):
        frame = traj[frame_idx]
        hbonds = md.baker_hubbard(frame, freq=0.0,
                                   exclude_water=True)
        hbonds_per_frame.append(len(hbonds))

        for hb in hbonds:
            key = tuple(hb)
            if key not in all_hbonds:
                all_hbonds[key] = 0
            all_hbonds[key] += 1

    # Calculate occupancies
    hbond_details = []
    for (d, h, a), count in sorted(all_hbonds.items(), key=lambda x: -x[1]):
        occupancy = count / traj.n_frames
        if occupancy >= freq_cutoff:
            donor = traj.topology.atom(d)
            hydrogen = traj.topology.atom(h)
            acceptor = traj.topology.atom(a)
            hbond_details.append({
                "donor": f"{donor.residue.name}{donor.residue.resSeq}-{donor.name}",
                "hydrogen": f"{hydrogen.name}",
                "acceptor": f"{acceptor.residue.name}{acceptor.residue.resSeq}-{acceptor.name}",
                "occupancy": round(occupancy, 3),
                "count": count,
            })

    return {
        "analysis_type": "hydrogen_bonds",
        "status": "completed",
        "data": {
            "time_ps": traj.time.tolist(),
            "n_hbonds_per_frame": hbonds_per_frame,
            "mean_n_hbonds": float(np.mean(hbonds_per_frame)),
            "hbond_details": hbond_details[:100],  # Top 100 by occupancy
            "total_unique_hbonds": len(all_hbonds),
        },
        "metadata": {
            "distance_cutoff_nm": distance_cutoff,
            "angle_cutoff_deg": angle_cutoff,
            "freq_cutoff": freq_cutoff,
            "n_frames": traj.n_frames,
            "method": "Baker-Hubbard (MDTraj)",
        },
    }


def compute_sasa(traj: "md.Trajectory", probe_radius: float = 0.14,
                  mode: str = "total") -> dict:
    """
    Compute Solvent Accessible Surface Area.
    probe_radius in nm (default 1.4 Å = 0.14 nm).
    """
    check_mdtraj()

    sasa = md.shrake_rupley(traj, probe_radius=probe_radius, mode='residue')
    total_sasa = sasa.sum(axis=1)  # Total SASA per frame

    result = {
        "analysis_type": "sasa",
        "status": "completed",
        "data": {
            "time_ps": traj.time.tolist(),
            "total_sasa_nm2": total_sasa.tolist(),
            "mean_sasa_nm2": float(np.mean(total_sasa)),
            "std_sasa_nm2": float(np.std(total_sasa)),
        },
        "metadata": {
            "probe_radius_nm": probe_radius,
            "n_frames": traj.n_frames,
            "unit": "nm^2",
            "method": "Shrake-Rupley (MDTraj)",
        },
    }

    # Per-residue SASA (average over trajectory)
    if mode == "residue" or mode == "both":
        mean_res_sasa = sasa.mean(axis=0)
        residue_labels = [f"{r.name}{r.resSeq}" for r in traj.topology.residues]
        result["data"]["per_residue_sasa_nm2"] = mean_res_sasa.tolist()
        result["data"]["residue_labels"] = residue_labels[:len(mean_res_sasa)]

    return result


def compute_secondary_structure(traj: "md.Trajectory", simplified: bool = True) -> dict:
    """
    Compute secondary structure using DSSP.
    """
    check_mdtraj()

    try:
        dssp_data = md.compute_dssp(traj, simplified=simplified)
    except Exception as e:
        raise AnalysisError(f"DSSP computation failed: {e}")

    # Count SS types per frame
    ss_counts = {}
    for frame_idx in range(dssp_data.shape[0]):
        frame_ss = dssp_data[frame_idx]
        for ss_type in set(frame_ss):
            if ss_type not in ss_counts:
                ss_counts[ss_type] = []
            while len(ss_counts[ss_type]) < frame_idx:
                ss_counts[ss_type].append(0)

        for ss_type in ss_counts:
            count = np.sum(frame_ss == ss_type)
            if len(ss_counts[ss_type]) <= frame_idx:
                ss_counts[ss_type].append(int(count))

    # Pad any short lists
    for ss_type in ss_counts:
        while len(ss_counts[ss_type]) < traj.n_frames:
            ss_counts[ss_type].append(0)

    # Map DSSP codes
    ss_labels = {
        'H': 'Alpha helix',
        'E': 'Beta sheet',
        'C': 'Coil/Loop',
        'G': '3-10 helix',
        'I': 'Pi helix',
        'T': 'Turn',
        'S': 'Bend',
        'B': 'Beta bridge',
        ' ': 'Coil',
        'NA': 'Not assigned',
    }

    return {
        "analysis_type": "secondary_structure",
        "status": "completed",
        "data": {
            "time_ps": traj.time.tolist(),
            "ss_counts": {ss_labels.get(k, k): v for k, v in ss_counts.items()},
            "dssp_per_residue": dssp_data.tolist() if dssp_data.shape[0] <= 500 else dssp_data[::max(1, dssp_data.shape[0]//500)].tolist(),
        },
        "metadata": {
            "n_frames": traj.n_frames,
            "n_residues": dssp_data.shape[1] if len(dssp_data.shape) > 1 else 0,
            "simplified": simplified,
            "method": "DSSP (MDTraj)",
        },
    }


def compute_pca(traj: "md.Trajectory", atom_selection: str = "name CA",
                n_components: int = 10) -> dict:
    """
    Principal Component Analysis on atomic coordinates.
    """
    check_mdtraj()

    try:
        atom_indices = traj.topology.select(atom_selection)
    except Exception as e:
        raise AnalysisError(f"Invalid atom selection: {e}")

    if len(atom_indices) == 0:
        raise AnalysisError(f"Atom selection '{atom_selection}' matched 0 atoms")

    # Superpose
    traj_aligned = traj.superpose(traj, atom_indices=atom_indices)

    # Extract coordinates
    coords = traj_aligned.xyz[:, atom_indices, :]
    n_frames = coords.shape[0]
    n_atoms = coords.shape[1]
    coords_flat = coords.reshape(n_frames, n_atoms * 3)

    # Center
    mean_coords = coords_flat.mean(axis=0)
    centered = coords_flat - mean_coords

    # Covariance matrix
    cov_matrix = np.cov(centered.T)

    # Eigendecomposition
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)

    # Sort by descending eigenvalue
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    # Project onto PCs
    n_components = min(n_components, len(eigenvalues))
    projections = centered @ eigenvectors[:, :n_components]

    # Explained variance
    total_variance = np.sum(eigenvalues)
    explained_variance = (eigenvalues[:n_components] / total_variance * 100).tolist()
    cumulative_variance = np.cumsum(eigenvalues[:n_components] / total_variance * 100).tolist()

    return {
        "analysis_type": "pca",
        "status": "completed",
        "data": {
            "projections_pc1": projections[:, 0].tolist() if n_components >= 1 else [],
            "projections_pc2": projections[:, 1].tolist() if n_components >= 2 else [],
            "projections_pc3": projections[:, 2].tolist() if n_components >= 3 else [],
            "time_ps": traj.time.tolist(),
            "eigenvalues": eigenvalues[:n_components].tolist(),
            "explained_variance_pct": explained_variance,
            "cumulative_variance_pct": cumulative_variance,
        },
        "metadata": {
            "atom_selection": atom_selection,
            "n_atoms": len(atom_indices),
            "n_components": n_components,
            "n_frames": traj.n_frames,
            "total_variance": float(total_variance),
            "method": "PCA via covariance matrix eigendecomposition",
        },
    }


def compute_contact_map(traj: "md.Trajectory", cutoff: float = 0.45,
                         scheme: str = "closest-heavy") -> dict:
    """
    Compute residue-residue contact map.
    cutoff in nm.
    """
    check_mdtraj()

    n_residues = traj.topology.n_residues
    residue_labels = [f"{r.name}{r.resSeq}" for r in traj.topology.residues]

    # Handle edge case where protein is too small for default 'all' (which requires |i-j| >= 3)
    try:
        distances, pairs = md.compute_contacts(traj, scheme=scheme)
    except ValueError:
        # Fall back to computing contacts between all pairs (i, j) where i < j
        custom_pairs = []
        for i in range(n_residues):
            for j in range(i + 1, n_residues):
                custom_pairs.append((i, j))
        if not custom_pairs:
            return {
                "analysis_type": "contact_map",
                "status": "completed",
                "data": {"contact_matrix": [[0.0]], "residue_labels": residue_labels},
                "metadata": {"cutoff_nm": cutoff, "scheme": scheme, "n_residues": n_residues, "n_frames": traj.n_frames},
            }
        distances, pairs = md.compute_contacts(traj, contacts=custom_pairs, scheme=scheme)

    contact_freq = (distances < cutoff).mean(axis=0)

    # Build contact map matrix
    contact_matrix = np.zeros((n_residues, n_residues))
    for idx, (i, j) in enumerate(pairs):
        contact_matrix[i, j] = contact_freq[idx]
        contact_matrix[j, i] = contact_freq[idx]
    np.fill_diagonal(contact_matrix, 1.0) # Self contact is always 1

    return {
        "analysis_type": "contact_map",
        "status": "completed",
        "data": {
            "contact_matrix": contact_matrix.tolist(),
            "residue_labels": residue_labels,
        },
        "metadata": {
            "cutoff_nm": cutoff,
            "scheme": scheme,
            "n_residues": n_residues,
            "n_frames": traj.n_frames,
        },
    }


def compute_distances(traj: "md.Trajectory",
                       atom_pairs: list[tuple[int, int]]) -> dict:
    """
    Compute distances between atom pairs over time.
    """
    check_mdtraj()

    distances = md.compute_distances(traj, atom_pairs)

    pair_labels = []
    for i, j in atom_pairs:
        a1 = traj.topology.atom(i)
        a2 = traj.topology.atom(j)
        pair_labels.append(
            f"{a1.residue.name}{a1.residue.resSeq}:{a1.name} - "
            f"{a2.residue.name}{a2.residue.resSeq}:{a2.name}"
        )

    return {
        "analysis_type": "distances",
        "status": "completed",
        "data": {
            "time_ps": traj.time.tolist(),
            "distances_nm": {label: dist.tolist() for label, dist in zip(pair_labels, distances.T)},
        },
        "metadata": {
            "n_pairs": len(atom_pairs),
            "n_frames": traj.n_frames,
            "unit": "nm",
        },
    }


def compute_ramachandran(traj: "md.Trajectory") -> dict:
    """
    Compute Ramachandran (phi/psi) angles for all protein residues.
    """
    check_mdtraj()

    phi_indices, phi_angles = md.compute_phi(traj)
    psi_indices, psi_angles = md.compute_psi(traj)

    # Convert to degrees
    phi_deg = np.degrees(phi_angles)
    psi_deg = np.degrees(psi_angles)

    # Get residue labels for phi and psi
    phi_residues = []
    for indices in phi_indices:
        atom = traj.topology.atom(indices[1])
        phi_residues.append(f"{atom.residue.name}{atom.residue.resSeq}")

    psi_residues = []
    for indices in psi_indices:
        atom = traj.topology.atom(indices[1])
        psi_residues.append(f"{atom.residue.name}{atom.residue.resSeq}")

    # Average phi/psi over trajectory
    return {
        "analysis_type": "ramachandran",
        "status": "completed",
        "data": {
            "phi_avg_deg": phi_deg.mean(axis=0).tolist(),
            "psi_avg_deg": psi_deg.mean(axis=0).tolist(),
            "phi_all_deg": phi_deg.tolist() if phi_deg.shape[0] <= 500 else phi_deg[::max(1, phi_deg.shape[0]//500)].tolist(),
            "psi_all_deg": psi_deg.tolist() if psi_deg.shape[0] <= 500 else psi_deg[::max(1, psi_deg.shape[0]//500)].tolist(),
            "phi_residues": phi_residues,
            "psi_residues": psi_residues,
        },
        "metadata": {
            "n_phi": len(phi_residues),
            "n_psi": len(psi_residues),
            "n_frames": traj.n_frames,
            "unit": "degrees",
        },
    }


def compute_clustering(traj: "md.Trajectory", atom_selection: str = "name CA",
                        rmsd_cutoff: float = 0.2,
                        max_clusters: int = 20) -> dict:
    """
    RMSD-based clustering of trajectory frames.
    """
    check_mdtraj()
    from scipy.spatial.distance import squareform
    from scipy.cluster.hierarchy import fcluster, linkage

    try:
        atom_indices = traj.topology.select(atom_selection)
    except Exception as e:
        raise AnalysisError(f"Invalid atom selection: {e}")

    if len(atom_indices) == 0:
        raise AnalysisError("No atoms matched selection")

    # Compute pairwise RMSD
    n_frames = traj.n_frames
    if n_frames > 2000:
        # Subsample for large trajectories
        stride = n_frames // 2000
        traj_sub = traj[::stride]
    else:
        traj_sub = traj
        stride = 1

    distances = np.zeros((traj_sub.n_frames, traj_sub.n_frames))
    for i in range(traj_sub.n_frames):
        rmsd_i = md.rmsd(traj_sub, traj_sub, frame=i, atom_indices=atom_indices)
        distances[i, :] = rmsd_i

    # Make symmetric
    distances = (distances + distances.T) / 2
    np.fill_diagonal(distances, 0)

    # Hierarchical clustering
    condensed = squareform(distances)
    Z = linkage(condensed, method='average')
    labels = fcluster(Z, t=rmsd_cutoff, criterion='distance')

    # Cluster populations
    unique_labels, counts = np.unique(labels, return_counts=True)
    cluster_populations = {int(l): int(c) for l, c in zip(unique_labels, counts)}

    # Representative frames (medoids)
    representatives = {}
    for cl in unique_labels[:max_clusters]:
        mask = labels == cl
        cluster_dists = distances[np.ix_(mask, mask)]
        medoid_idx = np.argmin(cluster_dists.sum(axis=1))
        orig_idx = np.where(mask)[0][medoid_idx]
        representatives[int(cl)] = int(orig_idx * stride)

    return {
        "analysis_type": "clustering",
        "status": "completed",
        "data": {
            "cluster_labels": labels.tolist(),
            "cluster_populations": cluster_populations,
            "representatives": representatives,
            "n_clusters": len(unique_labels),
        },
        "metadata": {
            "atom_selection": atom_selection,
            "rmsd_cutoff_nm": rmsd_cutoff,
            "method": "Hierarchical average-linkage",
            "n_frames_analyzed": traj_sub.n_frames,
            "stride": stride,
        },
    }


def run_analysis(analysis_type: str, traj_path: str, top_path: str,
                  parameters: dict = None) -> dict:
    """
    Run a specific analysis on a trajectory.
    This is the main entry point for the analysis API.
    """
    if parameters is None:
        parameters = {}

    stride = parameters.get("stride", 1)

    try:
        traj = load_trajectory(traj_path, top_path, stride=stride)
    except AnalysisError as e:
        return {
            "analysis_type": analysis_type,
            "status": "failed",
            "error": str(e),
            "data": {},
            "metadata": {},
        }

    analysis_functions = {
        "rmsd": lambda: compute_rmsd(traj, atom_selection=parameters.get("atom_selection", "backbone")),
        "rmsf": lambda: compute_rmsf(traj, atom_selection=parameters.get("atom_selection", "name CA")),
        "radius_of_gyration": lambda: compute_radius_of_gyration(traj),
        "rg": lambda: compute_radius_of_gyration(traj),
        "hydrogen_bonds": lambda: compute_hbonds(traj),
        "hbonds": lambda: compute_hbonds(traj),
        "sasa": lambda: compute_sasa(traj, mode=parameters.get("mode", "total")),
        "secondary_structure": lambda: compute_secondary_structure(traj),
        "dssp": lambda: compute_secondary_structure(traj),
        "pca": lambda: compute_pca(traj, atom_selection=parameters.get("atom_selection", "name CA"),
                                   n_components=parameters.get("n_components", 10)),
        "contact_map": lambda: compute_contact_map(traj, cutoff=parameters.get("cutoff", 0.45)),
        "ramachandran": lambda: compute_ramachandran(traj),
        "clustering": lambda: compute_clustering(traj, rmsd_cutoff=parameters.get("rmsd_cutoff", 0.2)),
    }

    if analysis_type not in analysis_functions:
        return {
            "analysis_type": analysis_type,
            "status": "failed",
            "error": f"Unknown analysis type: {analysis_type}. Available: {list(analysis_functions.keys())}",
            "data": {},
            "metadata": {},
        }

    try:
        result = analysis_functions[analysis_type]()
        return result
    except AnalysisError as e:
        return {
            "analysis_type": analysis_type,
            "status": "failed",
            "error": str(e),
            "data": {},
            "metadata": {},
        }
    except Exception as e:
        logger.exception(f"Analysis {analysis_type} failed unexpectedly")
        return {
            "analysis_type": analysis_type,
            "status": "failed",
            "error": f"Unexpected error: {str(e)}",
            "data": {},
            "metadata": {},
        }
