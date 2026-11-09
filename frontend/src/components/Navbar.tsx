import React, { useState } from 'react';
import {
  Activity,
  Layers,
  FileText,
  Settings,
  Cpu,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  FolderOpen,
  LineChart,
  PlayCircle,
  Zap,
} from 'lucide-react';
import { getBackendUrl, setBackendUrl } from '../api';
import { SystemStatus } from '../types';

interface NavbarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  systemStatus: SystemStatus | null;
  onRefreshStatus: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  setCurrentTab,
  systemStatus,
  onRefreshStatus,
}) => {
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [customUrl, setCustomUrl] = useState(getBackendUrl());
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSaveUrl = (e: React.FormEvent) => {
    e.preventDefault();
    setBackendUrl(customUrl);
    setSaveSuccess(true);
    setTimeout(() => {
      setSaveSuccess(false);
      setShowSettingsModal(false);
      onRefreshStatus();
    }, 800);
  };

  const gromacsOk = systemStatus?.gromacs?.available ?? false;
  const isGpu = systemStatus?.gromacs?.gpu_available ?? false;
  const activeBackendUrl = getBackendUrl();

  return (
    <>
      <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3 cursor-pointer" onClick={() => setCurrentTab('dashboard')}>
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-emerald-700 flex items-center justify-center shadow-lg shadow-teal-500/20">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div>
                <span className="text-lg font-black tracking-tight text-white flex items-center gap-1.5">
                  BioMD<span className="text-teal-400 font-normal">Studio</span>
                </span>
                <span className="block text-[10px] text-teal-500 font-mono tracking-wider uppercase -mt-1 font-semibold">
                  Online Molecular Dynamics
                </span>
              </div>
            </div>

            {/* Navigation Tabs */}
            <nav className="hidden md:flex items-center gap-1">
              {[
                { id: 'dashboard', label: 'Dashboard', icon: Layers },
                { id: 'new', label: 'New Simulation', icon: PlayCircle },
                { id: 'monitor', label: 'Job Monitor', icon: Activity },
                { id: 'analysis', label: 'Scientific Analysis', icon: LineChart },
                { id: 'files', label: 'Project Files', icon: FolderOpen },
                { id: 'colab', label: 'Free GPU Guide', icon: Zap },
                { id: 'docs', label: 'Documentation', icon: FileText },
              ].map((tab) => {
                const Icon = tab.icon;
                const active = currentTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setCurrentTab(tab.id)}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition ${
                      active
                        ? 'bg-teal-500/15 text-teal-400 border border-teal-500/30'
                        : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                );
              })}
            </nav>

            {/* Right: Engine / Backend Connection Status Pill */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowSettingsModal(true)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium transition shadow-sm ${
                  gromacsOk
                    ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/80 hover:border-emerald-600'
                    : 'bg-amber-950/40 text-amber-300 border-amber-800/80 hover:border-amber-600'
                }`}
                title="Configure Backend Connection"
              >
                <span className={`w-2 h-2 rounded-full ${gromacsOk ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
                <span className="hidden sm:inline">
                  {gromacsOk ? (isGpu ? 'GROMACS GPU Ready' : 'GROMACS CPU Ready') : 'Connect GPU Engine'}
                </span>
                <Settings className="w-3.5 h-3.5 opacity-70" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Backend Settings Modal */}
      {showSettingsModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative animate-in fade-in zoom-in-95 duration-150">
            <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-2">
              <Settings className="w-5 h-5 text-teal-400" /> Backend Engine Configuration
            </h3>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              BioMD Studio is designed to run <strong>real, un-fabricated MD simulations</strong> on genuine hardware. You can connect to your local machine or a <strong>free Google Colab GPU instance</strong> without per-simulation costs.
            </p>

            <form onSubmit={handleSaveUrl} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Backend API URL:
                </label>
                <input
                  type="text"
                  value={customUrl}
                  onChange={(e) => setCustomUrl(e.target.value)}
                  placeholder="e.g. http://127.0.0.1:8000 or https://xxxx.trycloudflare.com"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-teal-500 font-mono"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Leave empty for default local proxy (<code className="text-teal-400 font-mono">/api</code>).
                </p>
              </div>

              {/* Status info box */}
              <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3.5 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Current GROMACS:</span>
                  <span className={`font-semibold ${gromacsOk ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {gromacsOk ? `Installed (${systemStatus?.gromacs?.version || 'v2024'})` : 'Not Detected in this runtime'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">GPU Acceleration:</span>
                  <span className={`font-semibold ${isGpu ? 'text-emerald-400' : 'text-slate-500'}`}>
                    {isGpu ? 'Enabled (CUDA / OpenCL)' : 'Disabled (CPU only)'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">MDTraj Analysis Engine:</span>
                  <span className={`font-semibold ${systemStatus?.mdtraj?.available ? 'text-emerald-400' : 'text-red-400'}`}>
                    {systemStatus?.mdtraj?.available ? `Active (v${systemStatus?.mdtraj?.version})` : 'Not Available'}
                  </span>
                </div>
              </div>

              <div className="bg-teal-950/30 border border-teal-800/50 rounded-xl p-3 text-xs text-teal-300 flex items-start gap-2.5">
                <Zap className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-white">Need a free high-performance GPU?</span>
                  <p className="mt-0.5 text-teal-300/90 leading-relaxed">
                    Open our included <strong>Google Colab Notebook</strong>, click "Run All", and paste the generated Cloudflare tunnel URL above for free Tesla T4 GPU simulation power!
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setShowSettingsModal(false);
                      setCurrentTab('colab');
                    }}
                    className="inline-flex items-center gap-1 text-teal-400 hover:text-teal-300 font-semibold mt-1 underline"
                  >
                    Open Colab Step-by-Step Guide →
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowSettingsModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-200 transition"
                >
                  Close
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-lg text-xs font-bold bg-teal-500 hover:bg-teal-600 text-slate-950 transition flex items-center gap-1.5"
                >
                  {saveSuccess ? (
                    <>
                      <CheckCircle2 className="w-4 h-4" /> Saved!
                    </>
                  ) : (
                    'Save & Connect'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
