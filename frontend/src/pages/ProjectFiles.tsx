import React, { useEffect, useState } from 'react';
import {
  FolderOpen,
  Download,
  FileCode,
  FileText,
  Archive,
  RefreshCw,
  HardDrive,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { listJobFiles, getDownloadFileUrl, getExportZipUrl } from '../api';

interface ProjectFilesProps {
  jobId: string | null;
}

export const ProjectFiles: React.FC<ProjectFilesProps> = ({ jobId }) => {
  const [files, setFiles] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFiles = async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listJobFiles(jobId);
      setFiles(data.files || []);
    } catch (err: any) {
      setError(err.message || 'Failed to list job files');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, [jobId]);

  if (!jobId) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
        <FolderOpen className="w-8 h-8 text-slate-500 mx-auto mb-2" />
        <h3 className="text-base font-bold text-slate-300">No Simulation Selected</h3>
        <p className="text-xs text-slate-500 mt-1">Select a simulation to browse and download its generated output files.</p>
      </div>
    );
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-teal-400" /> Generated Simulation Files
            </h2>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
              {jobId.slice(0, 8)}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Download individual topologies, trajectories, coordinates, or the complete reproducibility package.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <a
            href={getExportZipUrl(jobId)}
            download
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow-md transition"
          >
            <Archive className="w-4 h-4" /> Download Complete ZIP Package
          </a>
          <button
            onClick={fetchFiles}
            disabled={loading}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            title="Refresh Files"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Files List */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {files.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            {loading ? 'Scanning job directory...' : 'No generated files found for this job yet.'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 font-mono">
                <tr>
                  <th className="p-3.5">Filename</th>
                  <th className="p-3.5">Category</th>
                  <th className="p-3.5">Description</th>
                  <th className="p-3.5">Size</th>
                  <th className="p-3.5 text-right">Download</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 font-mono text-slate-300">
                {files.map((f, i) => (
                  <tr key={i} className="hover:bg-slate-850/60 transition">
                    <td className="p-3.5 font-semibold text-white flex items-center gap-2">
                      <FileCode className="w-4 h-4 text-teal-400 shrink-0" />
                      {f.filename}
                    </td>
                    <td className="p-3.5">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] uppercase font-bold text-slate-400">
                        {f.category}
                      </span>
                    </td>
                    <td className="p-3.5 text-slate-400 font-sans">{f.description || '—'}</td>
                    <td className="p-3.5 text-slate-400">{formatBytes(f.size_bytes)}</td>
                    <td className="p-3.5 text-right">
                      <a
                        href={getDownloadFileUrl(jobId, f.filename)}
                        download
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-teal-400 border border-slate-700 text-[11px] font-sans font-semibold transition"
                      >
                        <Download className="w-3 h-3" /> Get File
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
