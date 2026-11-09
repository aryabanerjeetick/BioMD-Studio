import { Project, ProjectFile, ValidationReport, SimulationConfig, SimulationJob, SystemStatus, AnalysisResult } from './types';

// Stored backend URL (allows user to point to Google Colab GPU instance)
const STORAGE_KEY = 'biomd_backend_url';

export function getBackendUrl(): string {
  return localStorage.getItem(STORAGE_KEY) || '';
}

export function setBackendUrl(url: string): void {
  const cleanUrl = url.replace(/\/+$/, '');
  localStorage.setItem(STORAGE_KEY, cleanUrl);
}

function getBaseUrl(): string {
  const custom = getBackendUrl();
  return custom ? `${custom}/api` : '/api';
}

export function getWsUrl(jobId: string): string {
  const custom = getBackendUrl();
  if (custom) {
    const wsBase = custom.replace(/^http/, 'ws');
    return `${wsBase}/ws/jobs/${jobId}`;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/jobs/${jobId}`;
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${getBaseUrl()}${endpoint}`;
  const res = await fetch(url, options);
  if (!res.ok) {
    let errMessage = `Error ${res.status}: ${res.statusText}`;
    try {
      const errData = await res.json();
      if (errData.detail) {
        errMessage = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // Keep statusText
    }
    throw new Error(errMessage);
  }
  return res.json();
}

// ── System ─────────────────────────────────────────────────────────────
export async function getSystemStatus(): Promise<SystemStatus> {
  return request<SystemStatus>('/simulation/system-status');
}

export async function checkHealth(): Promise<{ status: string; gromacs_available: boolean; version?: string }> {
  return request<{ status: string; gromacs_available: boolean; version?: string }>('/health');
}

// ── Projects ───────────────────────────────────────────────────────────
export async function listProjects(): Promise<Project[]> {
  return request<Project[]>('/projects');
}

export async function createProject(data: { name: string; description?: string; simulation_type?: string; scientific_objective?: string }): Promise<Project> {
  return request<Project>('/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function getProject(id: string): Promise<Project> {
  return request<Project>(`/projects/${id}`);
}

export async function deleteProject(id: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/projects/${id}`, { method: 'DELETE' });
}

// ── Structures ─────────────────────────────────────────────────────────
export async function uploadStructure(projectId: string, file: File, role: string = 'auto'): Promise<ProjectFile> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('file_role', role);

  const res = await fetch(`${getBaseUrl()}/structures/upload/${projectId}`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function validateStructure(fileId: string): Promise<ValidationReport> {
  return request<ValidationReport>(`/structures/validate/${fileId}`, { method: 'POST' });
}

export async function listFiles(projectId: string): Promise<ProjectFile[]> {
  return request<ProjectFile[]>(`/structures/files/${projectId}`);
}

export function getFileContentUrl(fileId: string): string {
  return `${getBaseUrl()}/structures/content/${fileId}`;
}

export async function extractProtein(fileId: string, keepWaters: boolean = false, keepLigands: boolean = false): Promise<any> {
  return request<any>(`/structures/extract-protein/${fileId}?keep_waters=${keepWaters}&keep_ligands=${keepLigands}`, { method: 'POST' });
}

export async function extractLigand(fileId: string, ligandName: string): Promise<any> {
  return request<any>(`/structures/extract-ligand/${fileId}?ligand_name=${encodeURIComponent(ligandName)}`, { method: 'POST' });
}

// ── Simulation ─────────────────────────────────────────────────────────
export async function startSimulation(projectId: string, config: SimulationConfig): Promise<SimulationJob> {
  return request<SimulationJob>(`/simulation/start/${projectId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
}

export async function listJobs(projectId: string): Promise<SimulationJob[]> {
  return request<SimulationJob[]>(`/simulation/jobs/${projectId}`);
}

export async function getJob(jobId: string): Promise<SimulationJob> {
  return request<SimulationJob>(`/simulation/job/${jobId}`);
}

export async function cancelJob(jobId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/simulation/cancel/${jobId}`, { method: 'POST' });
}

// ── Analysis ───────────────────────────────────────────────────────────
export async function listAvailableAnalyses(): Promise<Record<string, any>> {
  return request<Record<string, any>>('/analysis/available');
}

export async function runJobAnalysis(jobId: string, analysisType: string, params: Record<string, any> = {}): Promise<AnalysisResult> {
  return request<AnalysisResult>(`/analysis/run/${jobId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ analysis_type: analysisType, parameters: params }),
  });
}

export async function getJobAnalysisResults(jobId: string): Promise<{ job_id: string; status: string; analyses: Record<string, AnalysisResult> }> {
  return request<{ job_id: string; status: string; analyses: Record<string, AnalysisResult> }>(`/analysis/results/${jobId}`);
}

export function getExportCsvUrl(jobId: string, analysisType: string): string {
  return `${getBaseUrl()}/analysis/export-csv/${jobId}/${analysisType}`;
}

// ── Files & Export ─────────────────────────────────────────────────────
export async function listJobFiles(jobId: string): Promise<{ job_id: string; files: any[] }> {
  return request<{ job_id: string; files: any[] }>(`/files/job/${jobId}`);
}

export function getDownloadFileUrl(jobId: string, filename: string): string {
  return `${getBaseUrl()}/files/download/${jobId}/${filename}`;
}

export function getExportZipUrl(jobId: string): string {
  return `${getBaseUrl()}/files/export-zip/${jobId}`;
}
