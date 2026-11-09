"""
GROMACS Engine — wraps GROMACS commands for the MD pipeline.
Executes REAL GROMACS commands — never fabricates results.
If GROMACS is unavailable, raises clear errors.
"""

import asyncio
import logging
import os
import shutil
import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import gromacs, FORCE_FIELD_INFO

logger = logging.getLogger(__name__)


class GromacsError(Exception):
    """Raised when a GROMACS command fails."""
    def __init__(self, message: str, command: str = "", returncode: int = -1,
                 stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class GromacsEngine:
    """
    Wraps GROMACS command execution.
    All methods execute real GROMACS commands and parse real outputs.
    """

    def __init__(self, work_dir: str):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.gmx = gromacs.gmx_path
        self.logs: list[dict] = []

        if not gromacs.available:
            raise GromacsError(
                "GROMACS is not installed or not found in PATH. "
                "Please install GROMACS (https://www.gromacs.org/) or set GMX_PATH environment variable."
            )

    async def _run_command(self, args: list[str], stdin_text: Optional[str] = None,
                           timeout: int = 3600, label: str = "") -> dict:
        """
        Run a GROMACS command and capture all output.
        Returns dict with stdout, stderr, returncode, elapsed time.
        """
        cmd = [self.gmx] + args
        cmd_str = " ".join(cmd)
        logger.info(f"Running GROMACS [{label}]: {cmd_str}")

        start_time = datetime.now(timezone.utc)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if stdin_text else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.work_dir),
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=stdin_text.encode() if stdin_text else None),
                timeout=timeout
            )

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

            result = {
                "command": cmd_str,
                "returncode": proc.returncode,
                "stdout": stdout.decode(errors='replace'),
                "stderr": stderr.decode(errors='replace'),
                "elapsed_seconds": elapsed,
                "label": label,
                "timestamp": start_time.isoformat(),
            }

            self.logs.append(result)

            if proc.returncode != 0:
                error_msg = stderr.decode(errors='replace')
                # Extract GROMACS error message
                fatal_match = re.search(r'Fatal error:.*?(?=\n\n|\Z)', error_msg, re.DOTALL)
                if fatal_match:
                    error_msg = fatal_match.group(0)
                raise GromacsError(
                    f"GROMACS command failed [{label}]: {error_msg}",
                    command=cmd_str,
                    returncode=proc.returncode,
                    stdout=stdout.decode(errors='replace'),
                    stderr=stderr.decode(errors='replace'),
                )

            return result

        except asyncio.TimeoutError:
            raise GromacsError(
                f"GROMACS command timed out after {timeout}s [{label}]",
                command=cmd_str,
            )

    async def pdb2gmx(self, input_pdb: str, force_field: str, water_model: str,
                       ignh: bool = True) -> dict:
        """
        Run pdb2gmx to generate topology.
        Returns paths to output files.
        """
        output_gro = str(self.work_dir / "protein_processed.gro")
        output_top = str(self.work_dir / "topol.top")
        output_itp = str(self.work_dir / "posre.itp")

        args = [
            "pdb2gmx",
            "-f", input_pdb,
            "-o", output_gro,
            "-p", output_top,
            "-i", output_itp,
            "-ff", force_field,
            "-water", water_model,
        ]
        if ignh:
            args.append("-ignh")

        result = await self._run_command(args, label="pdb2gmx")

        # Verify outputs exist
        outputs = {}
        for name, path in [("gro", output_gro), ("top", output_top)]:
            if os.path.exists(path):
                outputs[name] = path
            else:
                raise GromacsError(f"Expected output file not created: {path}")

        if os.path.exists(output_itp):
            outputs["posre_itp"] = output_itp

        outputs["log"] = result["stdout"] + result["stderr"]
        return outputs

    async def editconf(self, input_gro: str, box_type: str = "dodecahedron",
                        distance: float = 1.0) -> dict:
        """
        Define simulation box.
        """
        output_gro = str(self.work_dir / "protein_box.gro")

        args = [
            "editconf",
            "-f", input_gro,
            "-o", output_gro,
            "-c",  # Center
            "-d", str(distance),
            "-bt", box_type,
        ]

        result = await self._run_command(args, label="editconf")

        if not os.path.exists(output_gro):
            raise GromacsError("editconf did not create output file")

        # Parse box dimensions from output
        box_info = {}
        for line in result["stdout"].splitlines() + result["stderr"].splitlines():
            if "new box vectors" in line.lower():
                box_info["box_vectors"] = line.strip()
            elif "volume" in line.lower():
                box_info["volume"] = line.strip()

        return {"gro": output_gro, "box_info": box_info, "log": result["stderr"]}

    async def solvate(self, input_gro: str, topol: str,
                       solvent: str = "spc216.gro") -> dict:
        """
        Add solvent to the box.
        """
        output_gro = str(self.work_dir / "protein_solv.gro")

        args = [
            "solvate",
            "-cp", input_gro,
            "-cs", solvent,
            "-o", output_gro,
            "-p", topol,
        ]

        result = await self._run_command(args, label="solvate")

        if not os.path.exists(output_gro):
            raise GromacsError("solvate did not create output file")

        # Parse number of water molecules
        n_waters = 0
        for line in result["stderr"].splitlines() + result["stdout"].splitlines():
            match = re.search(r'Number of solvent molecules:\s*(\d+)', line)
            if match:
                n_waters = int(match.group(1))
                break

        return {"gro": output_gro, "n_waters": n_waters, "log": result["stderr"]}

    async def grompp(self, mdp_file: str, gro_file: str, top_file: str,
                      output_tpr: str, maxwarn: int = 0,
                      restraint_file: Optional[str] = None) -> dict:
        """
        Pre-process: generate TPR file.
        """
        args = [
            "grompp",
            "-f", mdp_file,
            "-c", gro_file,
            "-p", top_file,
            "-o", output_tpr,
            "-maxwarn", str(maxwarn),
        ]
        if restraint_file:
            args.extend(["-r", restraint_file])

        result = await self._run_command(args, label="grompp")

        if not os.path.exists(output_tpr):
            raise GromacsError(f"grompp did not create TPR file: {output_tpr}")

        # Extract warnings
        grompp_warnings = []
        for line in result["stderr"].splitlines():
            if "WARNING" in line or "warning" in line.lower():
                grompp_warnings.append(line.strip())

        return {"tpr": output_tpr, "warnings": grompp_warnings, "log": result["stderr"]}

    async def genion(self, input_tpr: str, topol: str,
                      pname: str = "NA", nname: str = "CL",
                      concentration: float = 0.15, neutral: bool = True) -> dict:
        """
        Add ions to neutralize system and set salt concentration.
        """
        output_gro = str(self.work_dir / "protein_ions.gro")

        args = [
            "genion",
            "-s", input_tpr,
            "-o", output_gro,
            "-p", topol,
            "-pname", pname,
            "-nname", nname,
            "-conc", str(concentration),
        ]
        if neutral:
            args.append("-neutral")

        # genion needs group selection — typically "SOL" group (usually 13)
        result = await self._run_command(args, stdin_text="SOL\n", label="genion")

        if not os.path.exists(output_gro):
            raise GromacsError("genion did not create output file")

        # Parse ion counts
        n_cations = 0
        n_anions = 0
        for line in result["stderr"].splitlines() + result["stdout"].splitlines():
            match = re.search(r'Will try to add (\d+)\s+(\w+)\s+ions and (\d+)\s+(\w+)', line)
            if match:
                n_cations = int(match.group(1))
                n_anions = int(match.group(3))
                break

        return {
            "gro": output_gro,
            "n_cations": n_cations,
            "n_anions": n_anions,
            "log": result["stderr"]
        }

    async def mdrun(self, tpr_file: str, output_prefix: str,
                     nsteps: Optional[int] = None,
                     ntomp: Optional[int] = None,
                     gpu_id: Optional[str] = None,
                     checkpoint: Optional[str] = None,
                     append: bool = False) -> dict:
        """
        Run MD simulation (energy minimization, equilibration, or production).
        """
        args = [
            "mdrun",
            "-s", tpr_file,
            "-deffnm", output_prefix,
            "-v",  # Verbose for progress
        ]

        if nsteps is not None:
            args.extend(["-nsteps", str(nsteps)])
        if ntomp is not None:
            args.extend(["-ntomp", str(ntomp)])
        if gpu_id is not None:
            args.extend(["-gpu_id", gpu_id])
        if checkpoint:
            args.extend(["-cpi", checkpoint])
        if append:
            args.append("-append")

        # Use longer timeout for production runs
        timeout = 86400  # 24 hours max
        result = await self._run_command(args, label=f"mdrun ({output_prefix})", timeout=timeout)

        # Check for output files
        outputs = {}
        for ext in ["gro", "edr", "log", "xtc", "trr", "cpt"]:
            fpath = str(self.work_dir / f"{output_prefix}.{ext}")
            if os.path.exists(fpath):
                outputs[ext] = fpath

        return {**outputs, "log_output": result["stderr"], "elapsed": result["elapsed_seconds"]}

    async def energy(self, edr_file: str, output_xvg: str,
                      terms: list[str]) -> dict:
        """
        Extract energy data from EDR file using gmx energy.
        """
        # Create selection string for energy terms
        stdin_text = "\n".join(terms) + "\n\n"

        args = [
            "energy",
            "-f", edr_file,
            "-o", output_xvg,
        ]

        result = await self._run_command(args, stdin_text=stdin_text, label="energy")

        # Parse XVG file
        data = parse_xvg(output_xvg)

        return {"xvg_file": output_xvg, "data": data, "log": result["stderr"]}

    async def trjconv(self, traj_file: str, tpr_file: str, output_file: str,
                       pbc: str = "mol", center: bool = True,
                       fit: Optional[str] = None,
                       group: str = "System") -> dict:
        """
        Process trajectory (PBC correction, centering, fitting).
        """
        args = [
            "trjconv",
            "-f", traj_file,
            "-s", tpr_file,
            "-o", output_file,
        ]
        if pbc:
            args.extend(["-pbc", pbc])
        if center:
            args.append("-center")
        if fit:
            args.extend(["-fit", fit])

        # Selection depends on options
        if center:
            stdin_text = "Protein\nSystem\n"
        else:
            stdin_text = f"{group}\n"

        result = await self._run_command(args, stdin_text=stdin_text, label="trjconv")

        if not os.path.exists(output_file):
            raise GromacsError(f"trjconv did not create output: {output_file}")

        return {"output": output_file, "log": result["stderr"]}

    def generate_mdp(self, stage: str, params: dict) -> str:
        """
        Generate MDP parameter file for a given simulation stage.
        Returns path to the generated MDP file.
        """
        mdp_content = self._build_mdp_content(stage, params)
        mdp_path = str(self.work_dir / f"{stage}.mdp")
        with open(mdp_path, 'w') as f:
            f.write(mdp_content)
        return mdp_path

    def _build_mdp_content(self, stage: str, params: dict) -> str:
        """Build MDP file content based on stage and parameters."""
        dt = params.get("dt", 0.002)
        temperature = params.get("temperature", 300.0)
        pressure = params.get("pressure", 1.0)
        constraints = params.get("constraints", "h-bonds")
        electrostatics = params.get("electrostatics", "PME")
        vdw_cutoff = params.get("vdw_cutoff", 1.0)
        coulomb_cutoff = params.get("coulomb_cutoff", 1.0)
        thermostat = params.get("thermostat", "v-rescale")
        barostat = params.get("barostat", "Parrinello-Rahman")

        if stage == "em":
            return f"""; Energy Minimization MDP
; Generated by MD Simulation Platform
integrator  = steep
emtol       = {params.get('em_tol', 1000.0)}
emstep      = 0.01
nsteps      = {params.get('em_steps', 50000)}

; Neighbor searching
nstlist         = 10
cutoff-scheme   = Verlet
ns_type         = grid

; Electrostatics
coulombtype     = {electrostatics}
rcoulomb        = {coulomb_cutoff}

; Van der Waals
rvdw            = {vdw_cutoff}

; Constraints
constraints     = none

; Output
nstxout         = 0
nstvout         = 0
nstenergy       = 500
nstlog          = 500
"""

        elif stage == "nvt":
            nsteps = params.get("nvt_steps", 50000)
            return f"""; NVT Equilibration MDP
; Generated by MD Simulation Platform
integrator  = md
dt          = {dt}
nsteps      = {nsteps}

; Output
nstxout-compressed  = {params.get('nstxout_compressed', 5000)}
nstenergy           = {params.get('nstenergy', 500)}
nstlog              = {params.get('nstlog', 500)}

; Neighbor searching
nstlist         = 10
cutoff-scheme   = Verlet
ns_type         = grid

; Electrostatics
coulombtype     = {electrostatics}
rcoulomb        = {coulomb_cutoff}
pme_order       = 4
fourierspacing  = 0.16

; Van der Waals
rvdw            = {vdw_cutoff}
DispCorr        = EnerPres

; Temperature coupling
tcoupl      = {thermostat}
tc-grps     = Protein Non-Protein
tau_t       = 0.1 0.1
ref_t       = {temperature} {temperature}

; Pressure coupling (OFF for NVT)
pcoupl      = no

; Constraints
constraints         = {constraints}
constraint_algorithm = lincs
lincs_iter          = 1
lincs_order         = 4

; PBC
pbc         = xyz

; Velocity generation
gen_vel     = yes
gen_temp    = {temperature}
gen_seed    = -1

; Position restraints
define      = -DPOSRES
"""

        elif stage == "npt":
            nsteps = params.get("npt_steps", 50000)
            return f"""; NPT Equilibration MDP
; Generated by MD Simulation Platform
integrator  = md
dt          = {dt}
nsteps      = {nsteps}

; Output
nstxout-compressed  = {params.get('nstxout_compressed', 5000)}
nstenergy           = {params.get('nstenergy', 500)}
nstlog              = {params.get('nstlog', 500)}

; Neighbor searching
nstlist         = 10
cutoff-scheme   = Verlet
ns_type         = grid

; Electrostatics
coulombtype     = {electrostatics}
rcoulomb        = {coulomb_cutoff}
pme_order       = 4
fourierspacing  = 0.16

; Van der Waals
rvdw            = {vdw_cutoff}
DispCorr        = EnerPres

; Temperature coupling
tcoupl      = {thermostat}
tc-grps     = Protein Non-Protein
tau_t       = 0.1 0.1
ref_t       = {temperature} {temperature}

; Pressure coupling
pcoupl          = {barostat}
pcoupltype      = isotropic
tau_p           = 2.0
ref_p           = {pressure}
compressibility = 4.5e-5

; Constraints
constraints         = {constraints}
constraint_algorithm = lincs
lincs_iter          = 1
lincs_order         = 4

; PBC
pbc         = xyz

; Velocity generation (continue from NVT)
gen_vel     = no
continuation = yes

; Position restraints
define      = -DPOSRES
"""

        elif stage == "prod":
            nsteps = params.get("prod_steps", 500000)
            nstxout_compressed = params.get("nstxout_compressed", 5000)
            nstenergy = params.get("nstenergy", 5000)
            return f"""; Production MD MDP
; Generated by MD Simulation Platform
integrator  = md
dt          = {dt}
nsteps      = {nsteps}

; Output
nstxout-compressed  = {nstxout_compressed}
nstenergy           = {nstenergy}
nstlog              = {nstenergy}
nstxout             = 0
nstvout             = 0
nstfout             = 0

; Neighbor searching
nstlist         = 10
cutoff-scheme   = Verlet
ns_type         = grid

; Electrostatics
coulombtype     = {electrostatics}
rcoulomb        = {coulomb_cutoff}
pme_order       = 4
fourierspacing  = 0.16

; Van der Waals
rvdw            = {vdw_cutoff}
DispCorr        = EnerPres

; Temperature coupling
tcoupl      = {thermostat}
tc-grps     = Protein Non-Protein
tau_t       = 0.1 0.1
ref_t       = {temperature} {temperature}

; Pressure coupling
pcoupl          = {barostat}
pcoupltype      = isotropic
tau_p           = 2.0
ref_p           = {pressure}
compressibility = 4.5e-5

; Constraints
constraints         = {constraints}
constraint_algorithm = lincs
lincs_iter          = 1
lincs_order         = 4

; PBC
pbc         = xyz

; Velocity generation (continue from NPT)
gen_vel     = no
continuation = yes
"""
        else:
            raise ValueError(f"Unknown MDP stage: {stage}")


def parse_xvg(filepath: str) -> dict:
    """
    Parse a GROMACS XVG file into structured data.
    Returns {columns: [...], data: [[...], ...], metadata: {...}}
    """
    columns = []
    data = []
    metadata = {"title": "", "xaxis": "", "yaxis": ""}

    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('@'):
                    if 'title' in line.lower():
                        metadata["title"] = line.split('"')[1] if '"' in line else ""
                    elif 'xaxis' in line.lower() and 'label' in line.lower():
                        metadata["xaxis"] = line.split('"')[1] if '"' in line else ""
                    elif 'yaxis' in line.lower() and 'label' in line.lower():
                        metadata["yaxis"] = line.split('"')[1] if '"' in line else ""
                    elif line.startswith('@ s') and 'legend' in line:
                        col_name = line.split('"')[1] if '"' in line else f"col_{len(columns)}"
                        columns.append(col_name)
                elif line.startswith('#') or line.startswith('&'):
                    continue
                elif line:
                    vals = line.split()
                    try:
                        data.append([float(v) for v in vals])
                    except ValueError:
                        continue
    except Exception as e:
        logger.error(f"Failed to parse XVG file {filepath}: {e}")
        return {"columns": [], "data": [], "metadata": metadata, "error": str(e)}

    if not columns and data:
        columns = [f"col_{i}" for i in range(len(data[0]) - 1)] if data else []

    return {"columns": ["time"] + columns, "data": data, "metadata": metadata}
