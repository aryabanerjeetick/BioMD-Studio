import React from 'react';
import {
  FileText,
  ShieldCheck,
  BookOpen,
  Atom,
  CheckCircle2,
  ExternalLink,
  Cpu,
  Layers,
} from 'lucide-react';

export const Docs: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Title */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/30 text-teal-400 text-xs font-semibold mb-3">
          <BookOpen className="w-3.5 h-3.5" /> Scientific Documentation & Protocol
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
          Molecular Dynamics Methodology & Provenance
        </h1>
        <p className="mt-2 text-slate-300 text-sm leading-relaxed">
          Comprehensive scientific principles, simulation parameters, and mathematical foundations implemented in BioMD Studio.
        </p>
      </div>

      {/* Non-Negotiable Scientific Integrity Rules */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-md space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-400" /> Scientific Authenticity Policy
        </h2>
        <div className="space-y-2 text-xs text-slate-300 leading-relaxed">
          <p>
            BioMD Studio is built for genuine computational research and academic publications. We strictly enforce:
          </p>
          <ul className="list-disc list-inside space-y-1.5 text-slate-400 font-sans pl-1">
            <li><strong>Zero Data Fabrication:</strong> No artificial, pre-loaded, or interpolated curves are ever generated to simulate a populated dashboard.</li>
            <li><strong>Real GROMACS Engine Execution:</strong> Every step (minimization, NVT, NPT, production MD) executes actual GROMACS binaries with full logging.</li>
            <li><strong>Mathematical Trajectory Analysis:</strong> RMSD, RMSF, Rg, SASA, H-bonds, and PCA are calculated directly from trajectory coordinates via MDTraj.</li>
            <li><strong>Complete Provenance:</strong> Software version, random seeds, force field parameters, and input SHA-256 checksums are tracked in every export manifest.</li>
          </ul>
        </div>
      </div>

      {/* Standard Simulation Protocol */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-md space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Layers className="w-5 h-5 text-teal-400" /> Standard 8-Stage MD Protocol
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <span className="text-teal-400 font-bold block">1. Topology & Protonation (pdb2gmx)</span>
            <p className="text-slate-400 font-sans leading-relaxed">
              Adds polar hydrogens, assigns protonation states at neutral pH (HIS, ASP, GLU, LYS), and generates OPLS/AMBER topology with bonded and non-bonded parameters.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <span className="text-teal-400 font-bold block">2. Solvation Box (editconf & solvate)</span>
            <p className="text-slate-400 font-sans leading-relaxed">
              Defines a periodic rhombic dodecahedron box with a minimum 1.0 nm margin from protein boundary, solvated with explicit 3-point TIP3P water molecules.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <span className="text-teal-400 font-bold block">3. Charge Neutralization (genion)</span>
            <p className="text-slate-400 font-sans leading-relaxed">
              Replaces random solvent molecules with Na⁺ and Cl⁻ counterions to neutralize total net charge and establish 0.15 M physiological ionic strength.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <span className="text-teal-400 font-bold block">4. Energy Minimization (em.mdp)</span>
            <p className="text-slate-400 font-sans leading-relaxed">
              Steepest descent integrator (50,000 steps) to resolve steric clashes and optimize bond geometry until Maximum Force &lt; 1000.0 kJ/mol/nm.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <span className="text-teal-400 font-bold block">5. NVT Equilibration (nvt.mdp)</span>
            <p className="text-slate-400 font-sans leading-relaxed">
              100 ps isochoric-isothermal equilibration at 300 K using the Bussi-Donadio-Parrinello velocity-rescaling thermostat with position restraints on heavy atoms.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <span className="text-teal-400 font-bold block">6. NPT Equilibration (npt.mdp)</span>
            <p className="text-slate-400 font-sans leading-relaxed">
              100 ps isobaric-isothermal equilibration at 1.0 bar using the Parrinello-Rahman barostat (compressibility: 4.5×10⁻⁵ bar⁻¹) to stabilize box volume and density.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <span className="text-teal-400 font-bold block">7. Production MD (prod.mdp)</span>
            <p className="text-slate-400 font-sans leading-relaxed">
              Unrestrained production MD using a 2.0 fs timestep with LINCS bond constraints, long-range Particle Mesh Ewald (PME) electrostatics, and Verlet cutoffs.
            </p>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <span className="text-teal-400 font-bold block">8. Trajectory Processing (trjconv)</span>
            <p className="text-slate-400 font-sans leading-relaxed">
              Rotational and translational fitting, periodic boundary condition (PBC) wrapping, and centering of the macromolecule for rigorous statistical analysis.
            </p>
          </div>
        </div>
      </div>

      {/* Software Citations */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-md space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-teal-400" /> Scientific Software Citations
        </h2>
        <div className="space-y-3 text-xs text-slate-400 font-mono">
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-200 font-bold">GROMACS:</span>
            <p className="mt-1 font-sans text-slate-400">
              Abraham, M. J. et al. (2015). GROMACS: High performance molecular simulations through multi-level parallelism from laptops to supercomputers. <em>SoftwareX</em>, 1–2, 19–25.
            </p>
          </div>

          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-200 font-bold">MDTraj:</span>
            <p className="mt-1 font-sans text-slate-400">
              McGibbon, R. T. et al. (2015). MDTraj: A Modern, Open Library for the Analysis of Molecular Dynamics Trajectories. <em>Biophysical Journal</em>, 109(8), 1528–1532.
            </p>
          </div>

          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-200 font-bold">Biopython:</span>
            <p className="mt-1 font-sans text-slate-400">
              Cock, P. J. A. et al. (2009). Biopython: freely available Python tools for computational molecular biology and bioinformatics. <em>Bioinformatics</em>, 25(11), 1422–1423.
            </p>
          </div>

          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-200 font-bold">AMBER99SB-ILDN Force Field:</span>
            <p className="mt-1 font-sans text-slate-400">
              Lindorff-Larsen, K. et al. (2010). Improved side-chain torsion potentials for the Amber ff99SB protein force field. <em>Proteins: Structure, Function, and Bioinformatics</em>, 78(8), 1950–1958.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
