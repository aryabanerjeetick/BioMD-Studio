import React, { useState } from 'react';
import {
  Zap,
  ExternalLink,
  CheckCircle2,
  Copy,
  Terminal,
  Cpu,
  ShieldCheck,
  ArrowRight,
  Server,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import { getBackendUrl, setBackendUrl, checkHealth } from '../api';

interface ColabGuideProps {
  onRefreshStatus: () => void;
}

export const ColabGuide: React.FC<ColabGuideProps> = ({ onRefreshStatus }) => {
  const [copied, setCopied] = useState<boolean>(false);
  const [testUrl, setTestUrl] = useState<string>(getBackendUrl());
  const [testing, setTesting] = useState<boolean>(false);
  const [testStatus, setTestStatus] = useState<'success' | 'failed' | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('');

  const copyPath = () => {
    navigator.clipboard.writeText('colab/MD_Simulation_Backend.ipynb');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTestAndSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!testUrl) return;

    setTesting(true);
    setTestStatus(null);
    setStatusMessage('Pinging backend endpoint...');

    try {
      const cleanUrl = testUrl.replace(/\/+$/, '');
      const res = await fetch(`${cleanUrl}/api/health`, { method: 'GET' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      setBackendUrl(cleanUrl);
      setTestStatus('success');
      setStatusMessage(`Connected! GROMACS: ${data.gromacs_available ? 'Available ✓' : 'Not detected'}, Version: ${data.gromacs_version || 'unknown'}`);
      onRefreshStatus();
    } catch (err: any) {
      setTestStatus('failed');
      setStatusMessage(`Connection failed: ${err.message}. Make sure the Colab cell is actively running.`);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Hero */}
      <div className="bg-gradient-to-r from-teal-950/40 via-slate-900 to-slate-900 border border-teal-800/40 rounded-2xl p-8 shadow-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/30 text-teal-400 text-xs font-semibold mb-4">
          <Zap className="w-4 h-4" /> 100% Free Cloud GPU Compute
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          Run GROMACS on Free Google Colab GPU
        </h1>
        <p className="mt-3 text-slate-300 text-sm leading-relaxed max-w-2xl">
          Don't stress your local laptop or drain your battery! You can run genuine GROMACS simulations and MDTraj analyses using Google's free NVIDIA Tesla T4 GPU workers with zero cloud subscription fees.
        </p>
      </div>

      {/* Step-by-Step Instructions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs">
        {/* Step 1 */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-3 flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-lg bg-teal-500/10 text-teal-400 flex items-center justify-center font-bold text-sm mb-3">
              1
            </div>
            <h3 className="text-sm font-bold text-slate-100">Open Notebook in Colab</h3>
            <p className="text-slate-400 mt-1 leading-relaxed">
              Open Google Colab (<a href="https://colab.research.google.com" target="_blank" rel="noreferrer" className="text-teal-400 underline">colab.research.google.com</a>) and upload the notebook included in this repository:
            </p>
            <div className="mt-2.5 p-2 bg-slate-950 rounded border border-slate-800 font-mono text-[11px] text-teal-300 flex items-center justify-between">
              <span className="truncate">colab/MD_Simulation_Backend.ipynb</span>
              <button onClick={copyPath} className="p-1 hover:text-white" title="Copy Path">
                {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
          <a
            href="https://colab.research.google.com"
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-center gap-1.5 w-full py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold transition"
          >
            Launch Google Colab <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        {/* Step 2 */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-3 flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-lg bg-teal-500/10 text-teal-400 flex items-center justify-center font-bold text-sm mb-3">
              2
            </div>
            <h3 className="text-sm font-bold text-slate-100">Select Free GPU & Run</h3>
            <p className="text-slate-400 mt-1 leading-relaxed">
              In Google Colab, go to <strong>Runtime → Change runtime type</strong>, select <strong>T4 GPU</strong> (free tier), and click <strong>Runtime → Run all</strong>.
            </p>
            <p className="text-slate-500 mt-2 text-[11px]">
              It automatically installs GROMACS with CUDA support, launches the backend, and opens a secure Cloudflare tunnel.
            </p>
          </div>
          <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-800 text-emerald-400 text-[11px] font-mono text-center">
            ✓ NVIDIA T4 GPU Enabled
          </div>
        </div>

        {/* Step 3 */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm space-y-3 flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-lg bg-teal-500/10 text-teal-400 flex items-center justify-center font-bold text-sm mb-3">
              3
            </div>
            <h3 className="text-sm font-bold text-slate-100">Connect to Web App</h3>
            <p className="text-slate-400 mt-1 leading-relaxed">
              The Colab cell outputs a public URL like:
              <br />
              <code className="text-teal-400 font-mono text-[11px]">https://xxxx.trycloudflare.com</code>
            </p>
            <p className="text-slate-500 mt-2 text-[11px]">
              Paste that URL in the box below to connect this web interface directly to your free GPU worker!
            </p>
          </div>
          <div className="p-2.5 rounded-lg bg-teal-950/40 border border-teal-800 text-teal-400 text-[11px] font-mono text-center">
            Ready to Simulate Real Trajectories
          </div>
        </div>
      </div>

      {/* Connect & Test Connection Box */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Server className="w-5 h-5 text-teal-400" /> Connect Your GPU Backend
        </h3>
        <p className="text-xs text-slate-400">
          Enter your active Colab Cloudflare tunnel URL or custom server endpoint:
        </p>

        <form onSubmit={handleTestAndSave} className="space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={testUrl}
              onChange={(e) => setTestUrl(e.target.value)}
              placeholder="e.g. https://xxxx-xxxx.trycloudflare.com"
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-teal-500 font-mono"
            />
            <button
              type="submit"
              disabled={testing || !testUrl}
              className="px-6 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow transition flex items-center gap-2 disabled:opacity-50"
            >
              {testing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              {testing ? 'Testing...' : 'Test & Save'}
            </button>
          </div>

          {statusMessage && (
            <div
              className={`p-3 rounded-lg text-xs font-mono flex items-center gap-2 ${
                testStatus === 'success'
                  ? 'bg-emerald-950/60 border border-emerald-800 text-emerald-300'
                  : 'bg-red-950/60 border border-red-800 text-red-300'
              }`}
            >
              {testStatus === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              )}
              <span>{statusMessage}</span>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};
