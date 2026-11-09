import React, { useState } from 'react';
import {
  Upload,
  CheckCircle2,
  AlertTriangle,
  FileText,
  PlayCircle,
  Layers,
  Sliders,
  Eye,
  Info,
  ShieldCheck,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  Zap,
} from 'lucide-react';
import { NGLViewer } from '../components/NGLViewer';
import {
  createProject,
  uploadStructure,
  validateStructure,
  startSimulation,
  getFileContentUrl,
} from '../api';
import { Project, ProjectFile, ValidationReport, SimulationConfig, SystemStatus } from '../types';

interface NewSimulationProps {
  systemStatus: SystemStatus | null;
  onJobStarted: (jobId: string, projectId: string) => void;
  onOpenColabGuide: () => void;
}

export const NewSimulation: React.FC<NewSimulationProps> = ({
  systemStatus,
  onJobStarted,
  onOpenColabGuide,
}) => {
  const [step, setStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Project Info
  const [projectName, setProjectName] = useState<string>('Kinase-Ligand Complex MD');
  const [projectDesc, setProjectDesc] = useState<string>('Molecular dynamics simulation of docked complex');
  const [simType, setSimType] = useState<string>('protein_ligand');

  // Created Project & Files
  const [project, setProject] = useState<Project | null>(null);
  const [uploadedFile, setUploadedFile] = useState<ProjectFile | null>(null);
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);

  // Simulation Parameters
  const [config, setConfig] = useState<SimulationConfig>({
    force_field: 'amber99sb-ildn',
    water_model: 'tip3p',
    box_type: 'dodecahedron',
    box_distance: 1.0,
    salt_concentration: 0.15,
    cation: 'NA',
    anion: 'CL',
    em_steps: 50000,
    em_tol: 1000.0,
    nvt_steps: 50000,
    npt_steps: 50000,
    temperature: 300.0,
    pressure: 1.0,
    dt: 0.002,
    prod_steps: 500000, // 1 ns at 2 fs
    nstxout_compressed: 5000, // Every 10 ps
    nstenergy: 5000,
    thermostat: 'v-rescale',
    barostat: 'Parrinello-Rahman',
    constraints: 'h-bonds',
    electrostatics: 'PME',
    vdw_cutoff: 1.0,
    coulomb_cutoff: 1.0,
  });

  const gromacsOk = systemStatus?.gromacs?.available ?? false;

  // Handle File Upload & Validation
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      // Create project if not exists
      let currentProject = project;
      if (!currentProject) {
        currentProject = await createProject({
          name: projectName,
          description: projectDesc,
          simulation_type: simType,
        });
        setProject(currentProject);
      }

      // Upload file
      const uploaded = await uploadStructure(currentProject.id, file, 'complex');
      setUploadedFile(uploaded);

      // Validate structure
      const report = await validateStructure(uploaded.id);
      setValidationReport(report);
    } catch (err: any) {
      setError(err.message || 'File upload and validation failed');
    } finally {
      setLoading(false);
    }
  };

  // Launch Simulation
  const handleStartSimulation = async () => {
    if (!project) return;
    setLoading(true);
    setError(null);

    try {
      const job = await startSimulation(project.id, config);
      onJobStarted(job.id, project.id);
    } catch (err: any) {
      setError(err.message || 'Failed to start simulation');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Wizard Step Indicator */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md">
        <div className="grid grid-cols-4 gap-2 text-xs font-semibold">
          {[
            { num: 1, label: '1. Project Info' },
            { num: 2, label: '2. Upload & Validate' },
            { num: 3, label: '3. System & Force Field' },
            { num: 4, label: '4. MD Parameters' },
          ].map((s) => (
            <div
              key={s.num}
              onClick={() => {
                if (s.num < step || (s.num === 2 && project) || (s.num > 2 && validationReport?.is_valid)) {
                  setStep(s.num);
                }
              }}
              className={`p-2.5 rounded-lg border text-center transition cursor-pointer ${
                step === s.num
                  ? 'bg-teal-500/20 border-teal-500/50 text-teal-300 font-bold'
                  : step > s.num
                  ? 'bg-slate-950/80 border-slate-800 text-slate-400 hover:text-slate-200'
                  : 'bg-slate-950/40 border-slate-900 text-slate-600 cursor-not-allowed'
              }`}
            >
              {s.label}
            </div>
          ))}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 text-red-400 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold">Error Notice:</span>
            <p className="leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {/* STEP 1: Project Information */}
      {step === 1 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-5">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-teal-400" /> Step 1: Project Configuration
          </h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            Name your simulation study and define its objective. This records full scientific provenance in your output manifests.
          </p>

          <div className="space-y-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1">Project Name:</label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-teal-500"
                placeholder="e.g. EGFR Kinase with Gefitinib MD"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1">Simulation Type:</label>
              <select
                value={simType}
                onChange={(e) => setSimType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-teal-500"
              >
                <option value="protein_ligand">Protein–Ligand Complex (Docked)</option>
                <option value="protein_only">Protein Only</option>
                <option value="nucleic_acid">Nucleic Acid / Complex</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1">Scientific Objective / Description:</label>
              <textarea
                value={projectDesc}
                onChange={(e) => setProjectDesc(e.target.value)}
                rows={3}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-teal-500"
                placeholder="Describe your research question (e.g. Assess binding pocket stability and H-bond persistence of the docked ligand over 10 ns)."
              />
            </div>
          </div>

          <div className="flex justify-end pt-3">
            <button
              onClick={() => setStep(2)}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow-lg transition"
            >
              Next: Upload Structure <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: Upload & Inspect Docked Structure */}
      {step === 2 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Upload className="w-5 h-5 text-teal-400" /> Step 2: Upload Docked Complex
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Upload your docked PDB / mmCIF / SDF file. The system performs genuine scientific structural validation.
              </p>
            </div>
          </div>

          {/* Upload Dropzone */}
          <div className="border-2 border-dashed border-slate-700 hover:border-teal-500/80 rounded-2xl p-8 text-center bg-slate-950/60 transition relative">
            <input
              type="file"
              accept=".pdb,.cif,.mmcif,.sdf,.mol2,.gro"
              onChange={handleFileUpload}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              disabled={loading}
            />
            <div className="w-12 h-12 rounded-full bg-teal-500/10 text-teal-400 flex items-center justify-center mx-auto mb-3">
              <Upload className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-slate-200">
              {loading ? 'Uploading & Validating Structure...' : 'Drop your docked PDB or click to browse'}
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Supports PDB, mmCIF, SDF, MOL2, GRO (Max 100 MB). File integrity verified via SHA-256.
            </p>
          </div>

          {/* Validation Report & 3D Viewer if uploaded */}
          {validationReport && uploadedFile && (
            <div className="space-y-6 pt-2">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 3D NGL Viewer */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                    <Eye className="w-4 h-4 text-teal-400" /> Interactive 3D Inspection
                  </h3>
                  <NGLViewer
                    structureUrl={getFileContentUrl(uploadedFile.id)}
                    fileExt={uploadedFile.file_type || 'pdb'}
                    height="380px"
                  />
                </div>

                {/* Scientific Validation Stats */}
                <div className="space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" /> Structure Validation Report
                  </h3>

                  <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs space-y-3 font-mono">
                    <div className="flex justify-between border-b border-slate-900 pb-2">
                      <span className="text-slate-500">Validation Status:</span>
                      <span className={`font-bold ${validationReport.is_valid ? 'text-emerald-400' : 'text-red-400'}`}>
                        {validationReport.is_valid ? '✓ VALIDATED STRUCTURE' : 'INVALID / ERRORS DETECTED'}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-slate-900 pb-2">
                      <span className="text-slate-500">Total Atoms:</span>
                      <span className="text-slate-200 font-semibold">{validationReport.n_atoms.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between border-b border-slate-900 pb-2">
                      <span className="text-slate-500">Protein Chains:</span>
                      <span className="text-slate-200">{validationReport.n_chains} ({validationReport.chains.map(c => c.chain_id).join(', ')})</span>
                    </div>
                    <div className="flex justify-between border-b border-slate-900 pb-2">
                      <span className="text-slate-500">Total Residues:</span>
                      <span className="text-slate-200">{validationReport.n_residues}</span>
                    </div>
                    <div className="flex justify-between border-b border-slate-900 pb-2">
                      <span className="text-slate-500">Disulfide Bonds:</span>
                      <span className="text-slate-200">{validationReport.disulfide_bonds.length} pairs identified</span>
                    </div>
                    <div className="flex justify-between border-b border-slate-900 pb-2">
                      <span className="text-slate-500">Crystallographic Waters:</span>
                      <span className="text-slate-200">{validationReport.n_waters} molecules</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Bound Ligands / HETATM:</span>
                      <span className="text-teal-400 font-semibold">
                        {validationReport.ligands.length > 0
                          ? validationReport.ligands.map(l => `${l.name} (${l.n_atoms} atoms)`).join(', ')
                          : 'None detected'}
                      </span>
                    </div>
                  </div>

                  {/* Warnings or Missing Residues */}
                  {validationReport.warnings.length > 0 && (
                    <div className="bg-amber-950/40 border border-amber-800/80 rounded-xl p-3 text-xs text-amber-300 space-y-1">
                      <span className="font-bold flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5" /> Quality Notes:
                      </span>
                      {validationReport.warnings.map((w, idx) => (
                        <p key={idx} className="text-slate-300 text-[11px] leading-relaxed">• {w}</p>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                <button
                  onClick={() => setStep(1)}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-slate-400 hover:text-slate-200 text-xs font-semibold"
                >
                  <ChevronLeft className="w-4 h-4" /> Back
                </button>
                <button
                  onClick={() => setStep(3)}
                  disabled={!validationReport.is_valid}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow-lg transition disabled:opacity-50"
                >
                  Next: Force Field & Solvation <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* STEP 3: Force Field, Solvation & Ions */}
      {step === 3 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-teal-400" /> Step 3: Force Field & Solvation Setup
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
            {/* Force Field */}
            <div className="space-y-4">
              <div>
                <label className="block font-semibold text-slate-300 mb-1">Protein Force Field:</label>
                <select
                  value={config.force_field}
                  onChange={(e) => setConfig({ ...config, force_field: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-teal-500"
                >
                  <option value="amber99sb-ildn">AMBER99SB-ILDN (Recommended for protein-ligand)</option>
                  <option value="amber03">AMBER03</option>
                  <option value="charmm27">CHARMM27 All-Atom</option>
                  <option value="oplsaa">OPLS-AA/L</option>
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  AMBER99SB-ILDN provides improved sidechain dihedral parameters verified by extensive benchmark data.
                </p>
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">Water Model:</label>
                <select
                  value={config.water_model}
                  onChange={(e) => setConfig({ ...config, water_model: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-teal-500"
                >
                  <option value="tip3p">TIP3P (3-Point, standard for AMBER)</option>
                  <option value="spce">SPC/E (Extended Simple Point Charge)</option>
                  <option value="tip4p">TIP4P (4-Point)</option>
                </select>
              </div>
            </div>

            {/* Solvation Box & Ions */}
            <div className="space-y-4">
              <div>
                <label className="block font-semibold text-slate-300 mb-1">Simulation Box Geometry:</label>
                <select
                  value={config.box_type}
                  onChange={(e) => setConfig({ ...config, box_type: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-teal-500"
                >
                  <option value="dodecahedron">Rhombic Dodecahedron (~29% fewer water atoms, optimal)</option>
                  <option value="cubic">Cubic Box</option>
                  <option value="octahedron">Truncated Octahedron</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">Box Margin (nm):</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.8"
                    max="2.5"
                    value={config.box_distance}
                    onChange={(e) => setConfig({ ...config, box_distance: parseFloat(e.target.value) || 1.0 })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-300 mb-1">NaCl Conc. (M):</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.0"
                    max="1.0"
                    value={config.salt_concentration}
                    onChange={(e) => setConfig({ ...config, salt_concentration: parseFloat(e.target.value) || 0.15 })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-teal-500"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-slate-800">
            <button
              onClick={() => setStep(2)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-slate-400 hover:text-slate-200 text-xs font-semibold"
            >
              <ChevronLeft className="w-4 h-4" /> Back
            </button>
            <button
              onClick={() => setStep(4)}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow-lg transition"
            >
              Next: MD Parameters <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: Molecular Dynamics Parameters & Launch */}
      {step === 4 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Sliders className="w-5 h-5 text-teal-400" /> Step 4: Molecular Dynamics Execution Parameters
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs">
            {/* Column 1: Minimization & Equilibration */}
            <div className="space-y-4 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
              <h3 className="font-bold text-slate-200 text-sm border-b border-slate-800 pb-2">
                1. EM & Equilibration
              </h3>

              <div>
                <label className="block text-slate-400 mb-1">Energy Minimization Steps:</label>
                <input
                  type="number"
                  value={config.em_steps}
                  onChange={(e) => setConfig({ ...config, em_steps: parseInt(e.target.value) || 50000 })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">NVT Steps (at {config.temperature} K):</label>
                <input
                  type="number"
                  value={config.nvt_steps}
                  onChange={(e) => setConfig({ ...config, nvt_steps: parseInt(e.target.value) || 50000 })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono"
                />
                <span className="text-[10px] text-slate-500">{(config.nvt_steps * config.dt).toFixed(1)} ps</span>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">NPT Steps (at {config.pressure} bar):</label>
                <input
                  type="number"
                  value={config.npt_steps}
                  onChange={(e) => setConfig({ ...config, npt_steps: parseInt(e.target.value) || 50000 })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono"
                />
                <span className="text-[10px] text-slate-500">{(config.npt_steps * config.dt).toFixed(1)} ps</span>
              </div>
            </div>

            {/* Column 2: Production MD */}
            <div className="space-y-4 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
              <h3 className="font-bold text-slate-200 text-sm border-b border-slate-800 pb-2">
                2. Production MD
              </h3>

              <div>
                <label className="block text-slate-400 mb-1">Production Steps:</label>
                <input
                  type="number"
                  value={config.prod_steps}
                  onChange={(e) => setConfig({ ...config, prod_steps: parseInt(e.target.value) || 500000 })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono"
                />
                <span className="text-[10px] text-teal-400 font-semibold font-mono">
                  Duration: {((config.prod_steps * config.dt) / 1000).toFixed(2)} ns ({config.prod_steps * config.dt} ps)
                </span>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Timestep dt (ps):</label>
                <input
                  type="number"
                  step="0.001"
                  value={config.dt}
                  onChange={(e) => setConfig({ ...config, dt: parseFloat(e.target.value) || 0.002 })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono"
                />
                <span className="text-[10px] text-slate-500">2.0 fs with LINCS constraints</span>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Save Trajectory Every (steps):</label>
                <input
                  type="number"
                  value={config.nstxout_compressed}
                  onChange={(e) => setConfig({ ...config, nstxout_compressed: parseInt(e.target.value) || 5000 })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 font-mono"
                />
                <span className="text-[10px] text-slate-500">
                  Every {(config.nstxout_compressed * config.dt).toFixed(1)} ps
                </span>
              </div>
            </div>

            {/* Column 3: Physics & Algorithms */}
            <div className="space-y-4 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
              <h3 className="font-bold text-slate-200 text-sm border-b border-slate-800 pb-2">
                3. Algorithms & Physics
              </h3>

              <div>
                <label className="block text-slate-400 mb-1">Thermostat:</label>
                <span className="block font-mono text-slate-200 py-1">{config.thermostat} (300 K)</span>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Barostat:</label>
                <span className="block font-mono text-slate-200 py-1">{config.barostat} (1.0 bar)</span>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Electrostatics:</label>
                <span className="block font-mono text-slate-200 py-1">PME (Particle Mesh Ewald)</span>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Cutoffs (vdW & Coulomb):</label>
                <span className="block font-mono text-slate-200 py-1">1.0 nm / 1.0 nm</span>
              </div>
            </div>
          </div>

          {/* GROMACS readiness notice */}
          {!gromacsOk && (
            <div className="bg-amber-950/40 border border-amber-800 rounded-xl p-4 text-xs text-amber-300 flex items-start justify-between gap-3">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-white">GROMACS is not detected on this machine</span>
                  <p className="mt-0.5 text-slate-300 leading-relaxed">
                    BioMD Studio upholds strict scientific integrity and <strong>never invents simulation results</strong>. You can run genuine GROMACS simulations for free on our Google Colab GPU backend!
                  </p>
                </div>
              </div>
              <button
                onClick={onOpenColabGuide}
                className="shrink-0 px-3.5 py-1.5 rounded-lg bg-teal-500 text-slate-950 font-bold text-xs flex items-center gap-1"
              >
                <Zap className="w-3.5 h-3.5" /> Open Colab GPU Guide
              </button>
            </div>
          )}

          <div className="flex items-center justify-between pt-4 border-t border-slate-800">
            <button
              onClick={() => setStep(3)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-slate-400 hover:text-slate-200 text-xs font-semibold"
            >
              <ChevronLeft className="w-4 h-4" /> Back
            </button>
            <button
              onClick={handleStartSimulation}
              disabled={loading || !gromacsOk}
              className="flex items-center gap-2 px-8 py-3 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400 text-slate-950 font-extrabold text-sm shadow-xl shadow-teal-500/20 transition active:scale-95 disabled:opacity-50"
            >
              <PlayCircle className="w-5 h-5" />
              {loading ? 'Submitting to GROMACS...' : 'Launch MD Simulation'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
