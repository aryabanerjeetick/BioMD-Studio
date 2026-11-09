import React from 'react';
import {
  Layers,
  PlayCircle,
  Activity,
  LineChart,
  FolderOpen,
  Zap,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Cpu,
} from 'lucide-react';
import { Project, SystemStatus } from '../types';

interface DashboardProps {
  projects: Project[];
  systemStatus: SystemStatus | null;
  onSelectProject: (project: Project) => void;
  onNewSimulation: () => void;
  onOpenColabGuide: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  projects,
  systemStatus,
  onSelectProject,
  onNewSimulation,
  onOpenColabGuide,
}) => {
  const gromacsOk = systemStatus?.gromacs?.available ?? false;
  const isGpu = systemStatus?.gromacs?.gpu_available ?? false;

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-teal-950/40 border border-slate-800 p-8 shadow-2xl">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/20 text-teal-400 text-xs font-semibold mb-4">
            <ShieldCheck className="w-3.5 h-3.5" /> 100% Genuine Computations • Scientific Integrity Certified
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight sm:text-4xl">
            Research-Grade Molecular Dynamics Platform
          </h1>
          <p className="mt-3 text-slate-300 text-sm leading-relaxed">
            Perform authentic biomolecular simulations online free of charge. Upload docked protein–ligand complexes, execute full GROMACS equilibration and production runs, and extract publication-ready trajectory analyses.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={onNewSimulation}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-sm shadow-lg shadow-teal-500/25 transition active:scale-95"
            >
              <PlayCircle className="w-4 h-4" /> Start New Simulation
            </button>
            <button
              onClick={onOpenColabGuide}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-sm border border-slate-700 transition"
            >
              <Zap className="w-4 h-4 text-teal-400" /> Free GPU Colab Guide
            </button>
          </div>
        </div>
      </div>

      {/* Engine Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: GROMACS Engine */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">MD Engine</span>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                gromacsOk
                  ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800'
                  : 'bg-amber-950/60 text-amber-400 border border-amber-800'
              }`}
            >
              {gromacsOk ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
              {gromacsOk ? 'Online' : 'Not Connected'}
            </span>
          </div>
          <div className="text-xl font-bold text-white mb-1">
            {gromacsOk ? `GROMACS ${systemStatus?.gromacs?.version || ''}` : 'No GROMACS Local'}
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            {gromacsOk
              ? `${isGpu ? 'NVIDIA GPU Acceleration Active.' : 'CPU Multithreading Active.'} Ready to compute real trajectories.`
              : 'Connect to our free Google Colab notebook in 1 click for free Tesla T4 GPU compute.'}
          </p>
        </div>

        {/* Card 2: Trajectory Analysis */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Analysis Suite</span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800">
              <CheckCircle2 className="w-3 h-3" /> MDTraj Ready
            </span>
          </div>
          <div className="text-xl font-bold text-white mb-1">MDTraj + SciPy</div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Real RMSD, RMSF, Radius of Gyration, SASA, H-bonds, PCA, and Contact Maps computed strictly from coordinates.
          </p>
        </div>

        {/* Card 3: Free GPU Worker */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Compute Backend</span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-teal-950/60 text-teal-400 border border-teal-800">
              <Zap className="w-3 h-3" /> Free Tier
            </span>
          </div>
          <div className="text-xl font-bold text-white mb-1">Google Colab Ready</div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Run real GROMACS simulations without heating your laptop. Zero cloud charges or subscription fees.
          </p>
        </div>
      </div>

      {/* Projects List Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-teal-400" /> Simulation Projects ({projects.length})
          </h2>
          <button
            onClick={onNewSimulation}
            className="text-xs font-semibold text-teal-400 hover:text-teal-300 flex items-center gap-1"
          >
            Create Project <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {projects.length === 0 ? (
          <div className="bg-slate-900/60 border border-dashed border-slate-800 rounded-2xl p-12 text-center">
            <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-3 text-slate-400">
              <FolderOpen className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200">No simulation projects yet</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-4">
              Get started by creating your first project and uploading a docked protein–ligand complex or PDB structure.
            </p>
            <button
              onClick={onNewSimulation}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow transition"
            >
              <PlayCircle className="w-4 h-4" /> Start New Simulation
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((p) => (
              <div
                key={p.id}
                onClick={() => onSelectProject(p)}
                className="bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-teal-500/50 rounded-xl p-5 cursor-pointer transition shadow-sm group flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h3 className="font-bold text-slate-100 group-hover:text-teal-400 transition text-sm">
                      {p.name}
                    </h3>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 uppercase">
                      {p.simulation_type.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2 mb-4 leading-relaxed">
                    {p.description || p.scientific_objective || 'No description provided.'}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {new Date(p.created_at).toLocaleDateString()}
                  </span>
                  <span>{p.file_count} files • {p.job_count} jobs</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
