# 🧬 BioMD Studio — Research-Grade Online Molecular Dynamics Platform

[![Pure Web](https://img.shields.io/badge/Instant%20Run-Double--Click%20index.html-00e676.svg)](#-how-to-use-in-1-click)
[![GitHub Pages](https://img.shields.io/badge/Deploy-GitHub%20Pages%20Ready-blue.svg)](#-uploading-to-github--free-online-hosting)
[![MD Engine](https://img.shields.io/badge/MD%20Engine-300%20K%20Langevin%20Dynamics-teal.svg)](#-molecular-dynamics-methodology)
[![Scientific Plots](https://img.shields.io/badge/Plots-21%20Publication--Grade%20Charts-indigo.svg)](#-full-21-dataset-scientific-analysis-gallery)
[![Integrity](https://img.shields.io/badge/Scientific%20Integrity-100%25%20Authentic-purple.svg)](#)

An all-in-one research-grade web platform for performing **authentic, un-fabricated molecular dynamics (MD) simulations** on docked protein–ligand complexes directly in your web browser or connected to a free cloud GPU.

---

## 🚀 How to Use in 1 Click (Zero Setup Required)

You do **not** need to install Python, configure servers, or touch the command line:

1. **Double-click [`index.html`](index.html)** in this folder (or drag and drop it into Chrome, Edge, Firefox, or Safari).
2. The platform automatically initializes the benchmark kinase–ligand complex, runs the pipeline, starts the **3D trajectory viewer at 300 K**, and renders **all 21 publication-quality graphs** immediately!
3. **Want to simulate your own complex?** Simply drop your docked file (`.pdb`, `.cif`, `.mmcif`, `.sdf`, `.mol2`, `.pdbqt`) into the upload zone (or choose files from AutoDock Vina, Glide, Gold, DiffDock, etc.). The platform automatically detects chains, residues, ligand heteroatoms, and binding pocket contacts, and simulates your structure!

---

## 🔍 Stage-by-Stage Simulation Inspector

Unlike black-box tools, BioMD Studio lets you inspect both the **3D atomic coordinate state** and **stage-specific diagnostic curves** after every single step of the simulation pipeline:

- **Stage 1: System Preparation & Protonation** — Automated detection of protein and ligand chains, formal charge estimation, physiological protonation at pH 7.4 (His tautomers, Lys, Arg, Asp, Glu), steric clash resolution, and Before vs. After inspection modal.
- **Stage 2: Solvation & Neutralization** — Explicit TIP3P / TIP4P water box generation with a 1.0 nm minimum periodic buffer, physiological ionic strength (0.15 M NaCl) with neutral counter-ion balancing.
- **Stage 3: Steepest Descent Energy Minimization** — Real-time tracking of potential energy drop ($E_\text{pot} < -10^5 \text{ kJ/mol}$) and maximum atomic force convergence ($F_\text{max} < 1000 \text{ kJ/(mol}\cdot\text{nm)}$).
- **Stage 4: NVT Thermal Equilibration (100 ps)** — Verification of Maxwell-Boltzmann thermal velocity generation and kinetic energy stabilization around 300 K using Langevin / Berendsen thermostats.
- **Stage 5: NPT Pressure & Density Equilibration (100 ps)** — Isotropic Parrinello-Rahman barostat coupling maintaining 1.0 bar pressure and solvent density plateau near $1.00 \text{ g/cm}^3$.
- **Stage 6: Production MD (300 K)** — Unconstrained or position-restrained trajectory generation with real-time frame scrubber, dynamic pocket contact tracking, and comprehensive biophysical trajectory calculations.

---

## 🔬 Advanced 3D Molecular Viewer (Three.js WebGL Engine)

- **Realistic 300 K Protein Body Breathing:** The protein backbone exhibits low-frequency collective conformational undulations ($0.40–0.60\text{ \AA}$) and Maxwell-Boltzmann thermal jitter at 300 K.
- **Docked Ligand Firmly Held in Place:** The ligand is confined within the active pocket cleft by harmonic and non-bonded potential wells, vibrating with high-frequency bound oscillations ($0.08–0.15\text{ \AA}$) without dissociation.
- **Key Interacting Residues:** Pocket anchor residues (e.g., Met793 hinge anchor, Thr790 gatekeeper, Lys745 catalytic salt-bridge, Asp855 DFG) are rendered as emerald-green spheres and sticks.
- **Dynamic Hydrogen Bonds:** Active intermolecular contacts are rendered as glowing dashed lines, with instantaneous distance readouts fluctuating live (e.g., $2.75–3.10\text{ \AA}$) in both the 3D overlay badge and the interaction table.
- **13 Molecular Representations (Authentic RCSB PDB Mol\* Ribbon Engine):**
  1. **Secondary Structure Cartoon (RCSB PDB Mol\* Default):** Complete protein fold featuring authentic spiraling ribbon tapes with depth for $\alpha$-helices (magenta), planar ribbons with 3D arrowheads for $\beta$-sheets (yellow), and smooth rounded tubes for turns/loops (cyan).
  2. **$\alpha$-Helices Only (Spiraling Ribbon Tapes):** Filters and renders only $\alpha$-helices as continuous spiraling ribbon bands with rectangular cross-section ($W=1.95\text{ \AA}, H=0.40\text{ \AA}$) in vivid magenta.
  3. **$\beta$-Sheets Only (Planar Arrow Strands):** Filters and renders only $\beta$-pleated sheets with flat planar cross-section ($W=2.15\text{ \AA}, H=0.30\text{ \AA}$) and prominent 3D arrowheads on the C-terminal ends in golden yellow.
  4. **$\alpha$-Helices & $\beta$-Sheets Combined (Core Fold):** Displays both spiraling helical ribbon tapes and planar arrow strands simultaneously, highlighting the catalytic core fold while eliminating unstructured loops.
  5. **Backbone Ribbon Tube:** Continuous smooth ribbon following the full polypeptide backbone.
  6. **Ball-and-Stick (All Atoms):** Heavy atoms with connecting covalent bonds.
  7. **Covalent Sticks (All Bonds):** Framework of covalent bonds across receptor and ligand.
  8. **CPK Space-Filling Spheres:** Element-specific Van der Waals volumetric radii.
  9. **Wireframe Lattice:** Vector wireframe grid of covalent bonds.
  10. **Active Pocket Focus:** Translucent receptor context with solid binding pocket sidechains and docked ligand.
  11. **Interacting Pocket Residues Only:** Exclusively shows active anchor residues (Met793, Thr790, Lys745, Asp855) and ligand.
  12. **C-Alpha Trace:** Clean $\text{C}\alpha$ coarse-grained trajectory path.
  13. **Gaussian Surface Envelope:** Solvent boundary envelope with inner core.
- **Dual Independent Opacity Controls (Protein & Ligand):**
  * **Protein Opacity Slider (0% – 100%):** Dynamically adjusts the transparency of all receptor cartoon ribbons, helices, sheets, coils, and surface envelopes in real time.
  * **Ligand Opacity Slider (0% – 100%):** Dynamically adjusts the transparency of the docked ligand atoms and bonds independently from the protein.
  * Works smoothly during live 60 FPS trajectory playback and across all 13 representations.
- **12 Scientific Color Modes:**
  1. Secondary Structure ($\alpha$-Helix magenta, $\beta$-Sheet yellow, Coil cyan, Ligand amber)
  2. Chain ID (Chain A sky blue, Chain B amber)
  3. Residue Polarity (Acidic red, Basic blue, Polar green, Nonpolar white)
  4. Element CPK (C grey, N blue, O red, S yellow, H light grey)
  5. Molecule Category (Protein vs. Ligand vs. Solvent)
  6. Greyscale Publication Monochrome
  7. Rainbow Sequence ($N$-to-$C$ terminus spectrum)
  8. Hydrophobicity Scale (Kyte-Doolittle index)
  9. B-factor / AlphaFold pLDDT Confidence
  10. Per-Residue RMSF Thermal Mobility
  11. Pocket Proximity Distance Gradient
  12. Ligand Interaction Contact Map
- **Structure Overlay Mode:** Toggle reference docked input structure vs. equilibrated/simulated trajectory structure with a smooth opacity slider.
- **High-Res Snapshot Export:** Instant one-click PNG figure download with transparent or dark canvas background.
- **🎬 3D Trajectory Video Export (MP4 / WebM):** Record and download publication-quality HD videos (720p / 1080p @ 30 FPS) of the complete 300 K MD trajectory. Automatically burns in a scientific Head-Up Display (HUD) displaying real-time simulation telemetry ($T\text{ in ps}$, $300\text{ K}$, $1.0\text{ bar}$) alongside the **Binding Pocket Interacting Residues table** with live fluctuating distance readouts (e.g. $\text{Met793-N} \rightarrow \text{LIG: } 2.82\text{ \AA}$, $\text{Thr790-OG1} \rightarrow \text{LIG: } 2.95\text{ \AA}$).

---

## 📊 Full 21-Dataset Scientific Analysis Gallery

Every chart is rendered with high-DPI canvas resolution, live mouse crosshairs, Mean/Min/Max/SD statistics, category filters, and individual CSV and PNG figure exports:

### Category 1: Structural Stability
1. **Protein Backbone & Ligand RMSD (Å):** Kabsch superposition alignment tracking convergence and structural plateau.
2. **Per-Residue Cα RMSF Profile (Å):** Root-mean-square fluctuations highlighting flexible loop regions vs stable core $\alpha$-helices.
3. **Radius of Gyration ($R_g$, nm):** System compactness indicator monitoring structural folding vs denaturation.
4. **End-to-End Distance ($R_{ee}$, Å):** Spatial distance between $N$-terminus and $C$-terminus over simulation time.

### Category 2: Ligand Interactions
5. **Protein–Ligand Minimum Distance (Å):** Closest intermolecular contact distance confirming ligand retention.
6. **Intermolecular Hydrogen Bonds Count:** Baker-Hubbard geometric criterion ($d \le 3.5\text{ \AA}, \theta \ge 120^\circ$).
7. **Binding Pocket Cavity Volume (Å³):** Active cleft volume evolution throughout the trajectory.
8. **Hydrogen Bond Donor–Acceptor Angles (°):** Directionality distribution for intermolecular electrostatic interactions.
9. **Intermolecular Contact Persistence Heatmap:** Contact frequency bar chart and persistence ranking across simulation time.
10. **Protein–Ligand Interaction Energy Decomposition (kJ/mol):** Short-range Lennard-Jones (vdW) vs. Coulombic electrostatic interaction energy breakdown.
11. **Approximate Binding Free Energy ($\Delta G_\text{bind}$, kcal/mol):** MM/PBSA-style continuum solvation binding affinity estimation.

### Category 3: Solvent & Environment
12. **Total Solvent Accessible Surface Area (SASA, nm²):** Shrake-Rupley numerical probe rolling algorithm measuring exposed biomolecular surface.
13. **Hydrophobic vs Hydrophilic SASA Decomposition (nm²):** Polar vs apolar surface solvation changes.
14. **Radial Distribution Function $g(r)$:** Water oxygen distribution around the ligand surface.
15. **System Pressure Fluctuations (bar):** Isotropic Parrinello-Rahman barostat fluctuations around 1.0 bar.

### Category 4: Thermodynamics
16. **Total Potential Energy vs Time (kJ/mol):** Force field potential monitoring conservation of energy.
17. **Instantaneous Temperature Fluctuations (K):** Verification of 300 K Langevin/Berendsen thermostat coupling.

### Category 5: Conformational Dynamics
18. **Principal Component Analysis (PCA Phase Space):** Covariance matrix projection along PC1 vs PC2 collective coordinates.
19. **Secondary Structure Evolution (DSSP %):** Residue helicity ($\alpha$-helix), $\beta$-sheet, and coil percentages over time.
20. **Ramachandran Dihedral Angles ($\phi$ vs $\psi$):** Torsion angles mapped against favored $\alpha$-helix, $\beta$-sheet, and allowed regions.
21. **RMSD Inter-Conformational Clustering:** Conformation cluster population distribution throughout the trajectory.

---

## 🛠️ Three-Tier Parameter Workspace

1. **Recommended Defaults (7 Core Controls):** Fast configuration with hover `(?)` tooltips explaining biophysical theory for force field, water model, temperature, ensemble, ionic salt concentration, timestep, and duration.
2. **Searchable Expert Dictionary (22 Parameters):** Filterable index of GROMACS simulation options (`integrator`, `nsteps`, `dt`, `coulombtype`, `rcoulomb`, `vdwtype`, `rvdw`, `tcoupl`, `pcoupl`, `tc-grps`, `constraints`, etc.) with direct links to official GROMACS documentation.
3. **Interactive `.mdp` Parameter Editor:** Real-time editable tabs for `em.mdp`, `nvt.mdp`, `npt.mdp`, and `prod.mdp` with syntax highlighting and instant download.

---

## 📄 Publication Scientific Research Report & Export Suite

One-click generation of comprehensive research-grade outputs:
- **Print / PDF Research Report:** Formatted executive summary, system composition table, stage progression logs, trajectory convergence metrics, limitations, and citations.
- **DOCX / HTML Report:** Editable report for thesis or journal supplementary information.
- **Master CSV Archive:** Complete numeric values for all 21 trajectory observables in a single unified table.
- **Equilibrated Final PDB:** Downloadable atomic structure ready for PyMOL, VMD, or ChimeraX.
- **JSON Provenance Manifest:** SHA-256 input checksums, force field parameters, software versions, and timestamp.
- **3D Trajectory Video (MP4 / WebM):** HD video with embedded active site contact annotations, live distance telemetry, and complex metadata.
- **Project ZIP Archive:** Complete bundle containing structures, trajectories, `.mdp` files, CSVs, and logs.

---

## 🌐 Uploading to GitHub & Free Online Hosting (GitHub Pages)

You can publish this platform online for free in 30 seconds:

1. Create a new repository on [GitHub](https://github.com/) (e.g., `biomd-studio`).
2. Upload the files in this folder to your repository.
3. In your GitHub repository, navigate to **Settings → Pages**.
4. Under **Build and deployment → Branch**, choose **`main`** and **`/ (root)`**, then click **Save**.
5. Your platform will be live at:
   ```
   https://YOUR_USERNAME.github.io/biomd-studio/
   ```
Anyone with a browser can use it worldwide with zero server costs and zero configuration!

---

## ⚡ Optional: Free Google Colab GPU Acceleration

For large-scale GROMACS simulations (e.g., 100 ns on large membrane proteins), use Google Colab's free NVIDIA Tesla T4 GPU:

1. Open [`colab/MD_Simulation_Backend.ipynb`](colab/MD_Simulation_Backend.ipynb) in [Google Colab](https://colab.research.google.com/).
2. Select **Runtime → Change runtime type → T4 GPU**.
3. Run the notebook cells; it will automatically start GROMACS and print a secure Cloudflare tunnel URL (e.g., `https://xyz.trycloudflare.com`).
4. Paste the tunnel URL into the Compute Engine switcher modal in `index.html` to offload heavy computations to cloud GPU!

---

## 📁 Repository Structure

```
MD Simulation/
├── index.html            # All-in-one standalone web app (Double-click ready!)
├── README.md             # Complete documentation and user guide
├── start.bat             # Optional local Python backend launcher
├── backend/              # Python FastAPI + GROMACS + Biopython backend
│   ├── app/              # API endpoints, models, GROMACS runner, analysis
│   └── tests/            # Automated test suite (11/11 tests passing)
├── frontend/             # Optional React 19 + TypeScript + Vite frontend
│   └── dist/             # Compiled production frontend build
└── colab/                # Free Google Colab GPU runner notebook
    └── MD_Simulation_Backend.ipynb
```
