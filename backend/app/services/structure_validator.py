"""
Structure validation service.
Parses and validates PDB, mmCIF, SDF, MOL2 files.
Uses Biopython for protein structures.
All validation is based on actual file content — never fabricated.
"""

import hashlib
import logging
import os
from pathlib import Path
from typing import Optional
from io import StringIO

from Bio.PDB import PDBParser, MMCIFParser, PDBIO, Select
from Bio.PDB.PDBExceptions import PDBConstructionWarning
from Bio.PDB.Polypeptide import is_aa, protein_letters_3to1

def three_to_one(resname: str) -> str:
    """Convert 3-letter amino acid code to 1-letter code."""
    return protein_letters_3to1.get(resname.upper(), 'X')
import warnings
import numpy as np

logger = logging.getLogger(__name__)

# Standard amino acids
STANDARD_RESIDUES = {
    'ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLN', 'GLU', 'GLY',
    'HIS', 'ILE', 'LEU', 'LYS', 'MET', 'PHE', 'PRO', 'SER',
    'THR', 'TRP', 'TYR', 'VAL'
}

# Common water residue names
WATER_RESIDUES = {'HOH', 'WAT', 'H2O', 'SOL', 'TIP', 'TIP3', 'TP3', 'TP4'}

# Common ions
ION_RESIDUES = {
    'NA', 'CL', 'MG', 'CA', 'ZN', 'FE', 'MN', 'CU', 'CO', 'NI',
    'K', 'BR', 'I', 'F', 'SO4', 'PO4', 'NA+', 'CL-', 'MG2+',
    'CA2+', 'ZN2+', 'FE2+', 'FE3+'
}

# Nucleic acid residues
NUCLEIC_ACID_RESIDUES = {
    'DA', 'DT', 'DC', 'DG', 'A', 'U', 'C', 'G',
    'ADE', 'THY', 'CYT', 'GUA', 'URA'
}

# Backbone atoms for protein
BACKBONE_ATOMS = {'N', 'CA', 'C', 'O'}


def compute_file_checksum(filepath: str) -> str:
    """Compute SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def detect_file_type(filepath: str) -> str:
    """
    Detect file type from content, not just extension.
    Returns: pdb, cif, sdf, mol2, gro, or unknown
    """
    try:
        with open(filepath, 'r', errors='replace') as f:
            first_lines = []
            for i, line in enumerate(f):
                first_lines.append(line)
                if i >= 50:
                    break
        content = ''.join(first_lines)

        # Check for PDB format
        pdb_records = {'ATOM  ', 'HETATM', 'HEADER', 'TITLE ', 'COMPND',
                       'SOURCE', 'REMARK', 'SEQRES', 'MODEL ', 'CRYST1'}
        pdb_score = sum(1 for line in first_lines if line[:6].rstrip() in pdb_records or line[:6] in pdb_records)
        if pdb_score >= 2:
            return "pdb"

        # Check for mmCIF format
        if content.startswith("data_") or "loop_" in content or "_atom_site." in content:
            return "cif"

        # Check for SDF/MOL format
        if "V2000" in content or "V3000" in content or "$$$$" in content:
            return "sdf"

        # Check for MOL2 format
        if "@<TRIPOS>" in content or "MOLECULE" in content:
            return "mol2"

        # Check for GRO format
        lines = first_lines
        if len(lines) >= 3:
            try:
                int(lines[1].strip())
                # GRO has atom count on line 2
                return "gro"
            except (ValueError, IndexError):
                pass

        # Check extension as fallback
        ext = Path(filepath).suffix.lower()
        ext_map = {
            '.pdb': 'pdb', '.ent': 'pdb',
            '.cif': 'cif', '.mmcif': 'cif',
            '.sdf': 'sdf', '.mol': 'sdf',
            '.mol2': 'mol2',
            '.gro': 'gro',
            '.pdbqt': 'pdbqt',
        }
        return ext_map.get(ext, "unknown")

    except Exception as e:
        logger.error(f"File type detection failed: {e}")
        return "unknown"


def validate_protein_structure(filepath: str) -> dict:
    """
    Validate a protein structure file (PDB or mmCIF).
    Returns a comprehensive validation report based on actual file content.
    """
    report = {
        "is_valid": False,
        "file_type": "",
        "n_models": 0,
        "n_chains": 0,
        "n_residues": 0,
        "n_atoms": 0,
        "chains": [],
        "missing_residues": [],
        "missing_atoms": [],
        "nonstandard_residues": [],
        "disulfide_bonds": [],
        "alternate_conformations": [],
        "has_waters": False,
        "n_waters": 0,
        "has_ligands": False,
        "ligands": [],
        "has_metals": False,
        "metals": [],
        "has_nucleic_acids": False,
        "warnings": [],
        "errors": [],
        "sequence": {},
    }

    file_type = detect_file_type(filepath)
    report["file_type"] = file_type

    if file_type not in ("pdb", "cif"):
        report["errors"].append(f"Expected PDB or mmCIF file, detected: {file_type}")
        return report

    # Parse structure
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", PDBConstructionWarning)

            if file_type == "pdb":
                parser = PDBParser(QUIET=False)
            else:
                parser = MMCIFParser(QUIET=False)

            structure = parser.get_structure("structure", filepath)

            # Collect parser warnings
            for warning in w:
                if issubclass(warning.category, PDBConstructionWarning):
                    report["warnings"].append(str(warning.message))

    except Exception as e:
        report["errors"].append(f"Failed to parse structure: {str(e)}")
        return report

    # Model count
    models = list(structure.get_models())
    report["n_models"] = len(models)
    if len(models) > 1:
        report["warnings"].append(
            f"Structure contains {len(models)} models. Only the first model will be used for simulation."
        )

    # Work with first model
    model = models[0]

    # Analyze chains
    all_atoms = 0
    all_residues = 0
    water_count = 0
    alt_confs = set()
    protein_chains = []

    for chain in model:
        chain_info = {
            "chain_id": chain.id,
            "n_residues": 0,
            "n_protein_residues": 0,
            "n_atoms": 0,
            "residue_range": "",
            "sequence": "",
        }

        protein_residues = []
        hetero_residues = []

        for residue in chain:
            hetflag = residue.id[0]
            resname = residue.resname.strip()
            resnum = residue.id[1]
            n_atoms_res = len(list(residue.get_atoms()))
            all_atoms += n_atoms_res
            all_residues += 1
            chain_info["n_atoms"] += n_atoms_res

            # Check for alternate conformations
            for atom in residue:
                if atom.is_disordered():
                    alt_confs.add((chain.id, resname, resnum))

            if hetflag == ' ' or hetflag == 'H_MSE':
                # Standard or modified residue
                if resname in STANDARD_RESIDUES:
                    chain_info["n_protein_residues"] += 1
                    chain_info["n_residues"] += 1
                    protein_residues.append(residue)
                    try:
                        one_letter = three_to_one(resname)
                        chain_info["sequence"] += one_letter
                    except KeyError:
                        chain_info["sequence"] += "X"
                elif resname in NUCLEIC_ACID_RESIDUES:
                    report["has_nucleic_acids"] = True
                    chain_info["n_residues"] += 1
                else:
                    # Nonstandard residue
                    report["nonstandard_residues"].append({
                        "chain": chain.id,
                        "name": resname,
                        "number": resnum,
                        "n_atoms": n_atoms_res,
                    })
                    chain_info["n_residues"] += 1
            elif resname in WATER_RESIDUES:
                water_count += 1
            elif resname in ION_RESIDUES or n_atoms_res <= 1:
                report["has_metals"] = True
                report["metals"].append({
                    "chain": chain.id,
                    "name": resname,
                    "number": resnum,
                })
            else:
                # Likely a ligand (HETATM with multiple atoms)
                if resname not in WATER_RESIDUES and resname not in ION_RESIDUES:
                    report["has_ligands"] = True
                    # Check if already added
                    existing = [l for l in report["ligands"] if l["name"] == resname and l["chain"] == chain.id]
                    if not existing:
                        report["ligands"].append({
                            "chain": chain.id,
                            "name": resname,
                            "number": resnum,
                            "n_atoms": n_atoms_res,
                        })

            chain_info["n_residues"] = max(chain_info["n_residues"], 0)

        # Check for missing backbone atoms in protein residues
        for res in protein_residues:
            atom_names = {a.name for a in res}
            missing = BACKBONE_ATOMS - atom_names
            if missing:
                report["missing_atoms"].append({
                    "chain": chain.id,
                    "residue": res.resname,
                    "number": res.id[1],
                    "missing": list(missing),
                })

        if chain_info["n_protein_residues"] > 0:
            residue_numbers = [r.id[1] for r in protein_residues]
            if residue_numbers:
                chain_info["residue_range"] = f"{min(residue_numbers)}-{max(residue_numbers)}"
            protein_chains.append(chain_info)

        report["chains"].append(chain_info)

    # Detect disulfide bonds (CYS pairs within 2.5 Å)
    cys_residues = []
    for chain in model:
        for residue in chain:
            if residue.resname in ('CYS', 'CYX') and 'SG' in [a.name for a in residue]:
                sg = [a for a in residue if a.name == 'SG'][0]
                cys_residues.append({
                    'chain': chain.id,
                    'resnum': residue.id[1],
                    'sg_coord': sg.get_vector().get_array(),
                })

    for i, cys1 in enumerate(cys_residues):
        for cys2 in cys_residues[i+1:]:
            dist = np.linalg.norm(
                np.array(cys1['sg_coord']) - np.array(cys2['sg_coord'])
            )
            if dist < 2.5:
                report["disulfide_bonds"].append({
                    "cys1_chain": cys1['chain'],
                    "cys1_resnum": cys1['resnum'],
                    "cys2_chain": cys2['chain'],
                    "cys2_resnum": cys2['resnum'],
                    "distance_angstrom": round(float(dist), 2),
                })

    # Populate report
    report["n_atoms"] = all_atoms
    report["n_residues"] = all_residues
    report["n_chains"] = len(list(model.get_chains()))
    report["has_waters"] = water_count > 0
    report["n_waters"] = water_count
    report["sequence"] = {c["chain_id"]: c["sequence"] for c in report["chains"] if c.get("sequence")}

    # Alternate conformations
    for ac in alt_confs:
        report["alternate_conformations"].append({
            "chain": ac[0], "residue": ac[1], "number": ac[2]
        })

    # Check for sequence gaps (missing residues)
    for chain_info in protein_chains:
        chain_id = chain_info["chain_id"]
        chain_obj = model[chain_id]
        protein_res = [r for r in chain_obj if r.id[0] == ' ' and r.resname in STANDARD_RESIDUES]
        if len(protein_res) >= 2:
            resnums = sorted([r.id[1] for r in protein_res])
            for i in range(len(resnums) - 1):
                gap = resnums[i+1] - resnums[i]
                if gap > 1:
                    report["missing_residues"].append({
                        "chain": chain_id,
                        "after_resnum": resnums[i],
                        "before_resnum": resnums[i+1],
                        "gap_size": gap - 1,
                    })

    if report["missing_residues"]:
        report["warnings"].append(
            f"Found {len(report['missing_residues'])} sequence gap(s). "
            "Missing residues have NOT been modeled and are absent from the structure."
        )

    # Set validity
    if len(report["errors"]) == 0 and report["n_atoms"] > 0:
        report["is_valid"] = True

    return report


def extract_protein_pdb(filepath: str, output_path: str,
                        keep_waters: bool = False,
                        keep_ligands: bool = False,
                        chains: Optional[list[str]] = None) -> dict:
    """
    Extract protein (and optionally other components) from a PDB/CIF file.
    Writes a clean PDB file suitable for GROMACS.
    Returns extraction report.
    """
    file_type = detect_file_type(filepath)

    if file_type == "pdb":
        parser = PDBParser(QUIET=True)
    elif file_type == "cif":
        parser = MMCIFParser(QUIET=True)
    else:
        return {"success": False, "error": f"Unsupported file type: {file_type}"}

    try:
        structure = parser.get_structure("protein", filepath)
    except Exception as e:
        return {"success": False, "error": f"Parse error: {str(e)}"}

    model = list(structure.get_models())[0]

    class ProteinSelect(Select):
        def accept_chain(self, chain):
            if chains and chain.id not in chains:
                return 0
            return 1

        def accept_residue(self, residue):
            hetflag = residue.id[0]
            resname = residue.resname.strip()

            # Always keep standard amino acids
            if hetflag == ' ' and resname in STANDARD_RESIDUES:
                return 1
            # Water
            if resname in WATER_RESIDUES:
                return 1 if keep_waters else 0
            # Ligands (HETATM, multi-atom)
            if hetflag.startswith('H_') or hetflag == 'W':
                if resname in WATER_RESIDUES:
                    return 1 if keep_waters else 0
                if resname in ION_RESIDUES:
                    return 0  # Remove ions; they'll be re-added
                return 1 if keep_ligands else 0
            return 1

        def accept_atom(self, atom):
            # Remove alternate conformations — keep 'A' or first
            if atom.is_disordered():
                return atom.get_altloc() == 'A' or atom.get_altloc() == ' '
            return 1

    io = PDBIO()
    io.set_structure(structure)
    io.save(str(output_path), ProteinSelect())

    # Verify output
    verify_parser = PDBParser(QUIET=True)
    verify_struct = verify_parser.get_structure("verify", str(output_path))
    verify_model = list(verify_struct.get_models())[0]
    n_atoms = sum(1 for _ in verify_model.get_atoms())
    n_residues = sum(1 for _ in verify_model.get_residues())

    return {
        "success": True,
        "output_path": str(output_path),
        "n_atoms": n_atoms,
        "n_residues": n_residues,
        "chains_extracted": [c.id for c in verify_model.get_chains()],
    }


def extract_ligand_from_pdb(filepath: str, ligand_name: str,
                             output_path: str, chain_id: Optional[str] = None) -> dict:
    """
    Extract a specific ligand (HETATM) from a PDB file.
    Writes a PDB file containing only the ligand atoms.
    """
    file_type = detect_file_type(filepath)
    if file_type == "pdb":
        parser = PDBParser(QUIET=True)
    elif file_type == "cif":
        parser = MMCIFParser(QUIET=True)
    else:
        return {"success": False, "error": f"Unsupported file type: {file_type}"}

    try:
        structure = parser.get_structure("struct", filepath)
    except Exception as e:
        return {"success": False, "error": f"Parse error: {str(e)}"}

    model = list(structure.get_models())[0]

    class LigandSelect(Select):
        def accept_chain(self, chain):
            if chain_id and chain.id != chain_id:
                return 0
            return 1

        def accept_residue(self, residue):
            return 1 if residue.resname.strip() == ligand_name else 0

    io = PDBIO()
    io.set_structure(structure)
    io.save(str(output_path), LigandSelect())

    # Verify
    verify = PDBParser(QUIET=True).get_structure("lig", str(output_path))
    n_atoms = sum(1 for _ in verify.get_atoms())

    if n_atoms == 0:
        return {
            "success": False,
            "error": f"Ligand '{ligand_name}' not found or has 0 atoms after extraction."
        }

    return {
        "success": True,
        "output_path": str(output_path),
        "n_atoms": n_atoms,
        "ligand_name": ligand_name,
    }
