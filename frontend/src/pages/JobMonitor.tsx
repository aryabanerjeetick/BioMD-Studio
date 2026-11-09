import React, { useEffect, useState, useRef } from 'react';
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  Clock,
  StopCircle,
  Terminal,
  LineChart,
  RefreshCw,
  FolderOpen,
  Cpu,
} from 'lucide-react';
import { getJob, cancelJob, getWsUrl } from '../api';
import { SimulationJob } from '../types';

interface JobMonitorProps {
  jobId: string | null;
  onOpenAnalysis: (jobId: string) => void;
  onOpenFiles: (jobId: string) => void;
}

export const JobMonitor: React.FC<JobMonitorProps> = ({
  jobId,
  onOpenAnalysis,
  onOpenFiles,
}) => {
  const [job, setJob] = useState<SimulationJob | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [isLive, setIsLive] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Fetch job details
  const fetchJob = async () => {
    if (!jobId) return;
    try {
      const data = await getJob(jobId);
      setJob(data);
      if (data.error_message) setError(data.error_message);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch job');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJob();
    const interval = setInterval(fetchJob, 4000);
    return () => clearInterval(interval);
  }, [jobId]);

  // Connect WebSocket for real-time progress
  useEffect(() => {
    if (!jobId) return;
    const wsUrl = getWsUrl(jobId);
    let ws: WebSocket;

    try {
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsLive(true);
        setLogs((prev) => [...prev, `[Connected to GROMACS Job Stream: ${jobId}]`]);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.message) {
            setLogs((prev) => [...prev, `[${data.stage}] ${data.message}`]);
          }
          if (data.status) {
            setJob((prev) => (prev ? { ...prev, status: data.status, current_stage: data.stage, progress_percent: data.progress } : null));
          }
        } catch {
          setLogs((prev) => [...prev, event.data]);
        }
      };

      ws.onerror = () => setIsLive(false);
      ws.onclose = () => setIsLive(false);
    } catch (e) {
      console.warn('WebSocket connection not supported in this mode:', e);
    }

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [jobId]);

  // Auto-scroll log window
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleCancel = async () => {
    if (!jobId) return;
    if (!confirm('Are you sure you want to stop this GROMACS simulation?')) return;
    try {
      await cancelJob(jobId);
      await fetchJob();
    } catch (err: any) {
      alert(`Cancel failed: ${err.message}`);
    }
  };

  if (!jobId) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
        <Activity className="w-8 h-8 text-slate-500 mx-auto mb-2 animate-pulse" />
        <h3 className="text-base font-bold text-slate-300">No Job Selected</h3>
        <p className="text-xs text-slate-500 mt-1">Start a simulation or select one from the Dashboard to monitor progress.</p>
      </div>
    );
  }

  const isFinished = job?.status === 'completed' || job?.status === 'completed_with_warnings';
  const isFailed = job?.status === 'failed';
  const isCancelled = job?.status === 'cancelled';
  const isRunning = !isFinished && !isFailed && !isCancelled;

  const stages = [
    { key: 'pdb2gmx', name: 'Topology' },
    { key: 'editconf', name: 'Box Definition' },
    { key: 'solvate', name: 'Solvation' },
    { key: 'genion', name: 'Ions & Neutralization' },
    { key: 'minimization', name: 'Energy Minimization' },
    { key: 'nvt', name: 'NVT (300K)' },
    { key: 'npt', name: 'NPT (1 bar)' },
    { key: 'production', name: 'Production MD' },
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Header & Status Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white">Simulation Monitor</h2>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                {jobId.slice(0, 8)}
              </span>
              {isLive && (
                <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-mono bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded-full">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span> Live WS
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Tracking real GROMACS execution stages and thermodynamics convergence.
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            {isRunning && (
              <button
                onClick={handleCancel}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-red-950/60 hover:bg-red-900/80 text-red-300 border border-red-800 transition"
              >
                <StopCircle className="w-3.5 h-3.5" /> Stop Simulation
              </button>
            )}

            {isFinished && (
              <button
                onClick={() => onOpenAnalysis(jobId)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-teal-500 hover:bg-teal-400 text-slate-950 shadow-md transition"
              >
                <LineChart className="w-4 h-4" /> View Scientific Analysis
              </button>
            )}

            <button
              onClick={() => onOpenFiles(jobId)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              <FolderOpen className="w-3.5 h-3.5" /> Simulation Files
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs font-mono">
            <span className="text-slate-300 font-medium">Stage: {job?.current_stage || 'Initializing'}</span>
            <span className="text-teal-400 font-bold">{job?.progress_percent?.toFixed(1) || 0}%</span>
          </div>
          <div className="w-full h-2.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-teal-500 to-emerald-400 transition-all duration-300"
              style={{ width: `${job?.progress_percent || 0}%` }}
            ></div>
          </div>
        </div>

        {/* Pipeline Stage Indicators */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 pt-2">
          {stages.map((st, i) => {
            const isCompletedStage = isFinished || (job?.progress_percent || 0) > ((i + 1) * 100) / stages.length;
            const isCurrent = job?.current_stage?.toLowerCase().includes(st.key);
            return (
              <div
                key={st.key}
                className={`p-2 rounded-lg border text-center text-[10px] font-semibold transition ${
                  isCompletedStage
                    ? 'bg-emerald-950/40 border-emerald-800/80 text-emerald-300'
                    : isCurrent
                    ? 'bg-teal-500/20 border-teal-500 text-teal-300 animate-pulse'
                    : 'bg-slate-950/60 border-slate-900 text-slate-500'
                }`}
              >
                <div className="truncate">{st.name}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Energy Minimization Convergence Banner (if EM completed) */}
      {job?.em_initial_energy !== null && job?.em_initial_energy !== undefined && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm text-xs">
          <h3 className="font-bold text-slate-200 mb-2 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Real Energy Minimization Convergence Data
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 font-mono">
            <div>
              <span className="text-slate-500 block">Initial Potential Energy:</span>
              <span className="text-slate-300 font-semibold">{job.em_initial_energy?.toFixed(2)} kJ/mol</span>
            </div>
            <div>
              <span className="text-slate-500 block">Final Potential Energy:</span>
              <span className="text-emerald-400 font-semibold">{job.em_final_energy?.toFixed(2)} kJ/mol</span>
            </div>
            <div>
              <span className="text-slate-500 block">Maximum Force (Fmax):</span>
              <span className="text-teal-400 font-semibold">{job.em_max_force?.toFixed(2) || '—'}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Status:</span>
              <span className="text-emerald-400 font-semibold">
                {job.em_converged ? '✓ CONVERGED' : 'TERMINATED'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Real GROMACS Execution Log Stream */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-teal-400" /> GROMACS Output Console
          </h3>
          <span className="text-[11px] font-mono text-slate-500">
            Engine: {job?.gromacs_version || 'GROMACS'}
          </span>
        </div>

        <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-300 h-80 overflow-y-auto space-y-1 leading-relaxed">
          {logs.length === 0 ? (
            <p className="text-slate-600">Waiting for engine output...</p>
          ) : (
            logs.map((line, i) => (
              <div key={i} className="whitespace-pre-wrap">
                {line}
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
};
