export interface Project {
  id: string;
  name: string;
  description: string;
  simulation_type: string;
  scientific_objective: string;
  created_at: string;
  updated_at: string;
  file_count: number;
  job_count: number;
}

export interface ProjectFile {
  id: string;
  filename: string;
  original_filename: string;
  file_type?: string;
  file_role?: string;
  file_size?: number;
  checksum?: string;
  validation_status: string;
  validation_report: ValidationReport;
  uploaded_at: string;
}

export interface ValidationReport {
  is_valid: boolean;
  file_type: string;
  n_models: number;
  n_chains: number;
  n_residues: number;
  n_atoms: number;
  chains: Array<{
    chain_id: string;
    n_residues: number;
    n_protein_residues: number;
    n_atoms: number;
    residue_range: string;
    sequence: string;
  }>;
  missing_residues: Array<{
    chain: string;
    after_resnum: number;
    before_resnum: number;
    gap_size: number;
  }>;
  missing_atoms: Array<{
    chain: string;
    residue: string;
    number: number;
    missing: string[];
  }>;
  nonstandard_residues: Array<{
    chain: string;
    name: string;
    number: number;
    n_atoms: number;
  }>;
  disulfide_bonds: Array<{
    cys1_chain: string;
    cys1_resnum: number;
    cys2_chain: string;
    cys2_resnum: number;
    distance_angstrom: number;
  }>;
  has_waters: boolean;
  n_waters: number;
  has_ligands: boolean;
  ligands: Array<{
    chain: string;
    name: string;
    number: number;
    n_atoms: number;
  }>;
  has_metals: boolean;
  metals: Array<{
    chain: string;
    name: string;
    number: number;
  }>;
  warnings: string[];
  errors: string[];
  sequence: Record<string, string>;
}

export interface SimulationConfig {
  force_field: string;
  water_model: string;
  box_type: string;
  box_distance: number;
  salt_concentration: number;
  cation: string;
  anion: string;
  em_steps: number;
  em_tol: number;
  nvt_steps: number;
  npt_steps: number;
  temperature: number;
  pressure: number;
  dt: number;
  prod_steps: number;
  nstxout_compressed: number;
  nstenergy: number;
  thermostat: string;
  barostat: string;
  constraints: string;
  electrostatics: string;
  vdw_cutoff: number;
  coulomb_cutoff: number;
}

export interface SimulationJob {
  id: string;
  project_id: string;
  status: string;
  current_stage: string;
  progress_percent: number;
  force_field: string;
  water_model: string;
  n_total_atoms: number;
  started_at?: string;
  completed_at?: string;
  elapsed_seconds?: number;
  error_message: string;
  error_stage: string;
  warnings: string[];
  gromacs_version: string;
  em_initial_energy?: number;
  em_final_energy?: number;
  em_max_force?: number;
  em_converged?: boolean;
  created_at: string;
}

export interface SystemStatus {
  gromacs: {
    available: boolean;
    path?: string;
    version?: string;
    gpu_available: boolean;
    force_fields: string[];
  };
  mdtraj: {
    available: boolean;
    version?: string;
  };
  force_fields: Record<string, {
    name: string;
    family: string;
    description: string;
    water_models: string[];
    default_water: string;
    reference: string;
  }>;
  water_models: Record<string, {
    name: string;
    atoms: number;
    description: string;
  }>;
  limits: {
    max_concurrent_jobs: number;
    active_jobs: number;
  };
}

export interface AnalysisResult {
  analysis_type: string;
  status: string;
  data: Record<string, any>;
  metadata: Record<string, any>;
  warnings?: string[];
  error?: string;
}
