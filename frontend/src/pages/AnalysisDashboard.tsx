import React, { useEffect, useState } from 'react';
import {
  LineChart,
  Activity,
  Download,
  Play,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Sliders,
  Sparkles,
  Layers,
  Table,
} from 'lucide-react';
import { ScientificPlot } from '../components/ScientificPlot';
import {
  getJobAnalysisResults,
  runJobAnalysis,
  getExportCsvUrl,
  listAvailableAnalyses,
} from '../api';
import { AnalysisResult } from '../types';

interface AnalysisDashboardProps {
  jobId: string | null;
}

export const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({ jobId }) => {
  const [analyses, setAnalyses] = useState<Record<string, AnalysisResult>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [computingType, setComputingType] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'rmsd' | 'rmsf' | 'rg' | 'sasa' | 'hbonds' | 'pca' | 'contacts'>('rmsd');

  // Load existing analysis results for this job
  const loadResults = async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getJobAnalysisResults(jobId);
      setAnalyses(res.analyses || {});
    } catch (err: any) {
      setError(err.message || 'Failed to load analysis results');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadResults();
  }, [jobId]);

  // Compute a specific analysis on-demand
  const handleRunAnalysis = async (type: string, params: Record<string, any> = {}) => {
    if (!jobId) return;
    setComputingType(type);
    setError(null);

    try {
      const res = await runJobAnalysis(jobId, type, params);
      if (res.status === 'failed') {
        setError(res.error || `Analysis ${type} computation failed`);
      } else {
        setAnalyses((prev) => ({ ...prev, [type]: res }));
      }
    } catch (err: any) {
      setError(err.message || `Failed to run ${type}`);
    } finally {
      setComputingType(null);
    }
  };

  if (!jobId) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center">
        <LineChart className="w-8 h-8 text-slate-500 mx-auto mb-2" />
        <h3 className="text-base font-bold text-slate-300">No Simulation Selected</h3>
        <p className="text-xs text-slate-500 mt-1">Select a completed simulation job to inspect scientific analysis.</p>
      </div>
    );
  }

  const rmsdRes = analyses['rmsd'];
  const rmsfRes = analyses['rmsf'];
  const rgRes = analyses['radius_of_gyration'] || analyses['rg'];
  const sasaRes = analyses['sasa'];
  const hbondsRes = analyses['hydrogen_bonds'] || analyses['hbonds'];
  const pcaRes = analyses['pca'];
  const contactRes = analyses['contact_map'];

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
            <LineChart className="w-6 h-6 text-teal-400" /> Scientific Trajectory Analysis
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Publication-quality observables computed with mathematical precision using MDTraj and SciPy.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadResults}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh Data
          </button>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-300 text-xs flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Analysis Calculation Notice:</span>
            <p className="mt-0.5 text-slate-300 leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-1.5 bg-slate-900 border border-slate-800 p-1.5 rounded-xl text-xs font-semibold">
        {[
          { id: 'rmsd', label: 'Backbone RMSD', result: rmsdRes },
          { id: 'rmsf', label: 'Residue RMSF', result: rmsfRes },
          { id: 'rg', label: 'Radius of Gyration', result: rgRes },
          { id: 'sasa', label: 'Solvent Area (SASA)', result: sasaRes },
          { id: 'hbonds', label: 'Hydrogen Bonds', result: hbondsRes },
          { id: 'pca', label: 'Essential Dynamics (PCA)', result: pcaRes },
          { id: 'contacts', label: 'Contact Map', result: contactRes },
        ].map((tab) => {
          const isCurrent = activeTab === tab.id;
          const isCalculated = Boolean(tab.result?.data);
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg transition ${
                isCurrent
                  ? 'bg-teal-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <span>{tab.label}</span>
              {isCalculated && (
                <span className={`w-1.5 h-1.5 rounded-full ${isCurrent ? 'bg-slate-950' : 'bg-emerald-400'}`}></span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB CONTENT: RMSD */}
      {activeTab === 'rmsd' && (
        <div className="space-y-4">
          {!rmsdRes?.data?.time_ps ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-3">
              <h3 className="text-sm font-bold text-slate-200">Root Mean Square Deviation (RMSD)</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Calculates the deviation of backbone atomic coordinates from the reference structure over simulation time.
              </p>
              <button
                onClick={() => handleRunAnalysis('rmsd', { atom_selection: 'backbone' })}
                disabled={computingType === 'rmsd'}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow transition disabled:opacity-50"
              >
                {computingType === 'rmsd' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {computingType === 'rmsd' ? 'Computing Backbone RMSD...' : 'Compute Backbone RMSD'}
              </button>
            </div>
          ) : (
            <ScientificPlot
              title="Protein Backbone RMSD vs Time"
              description="Evaluates global structural convergence and conformational stability of the protein."
              xLabel="Time (ps)"
              yLabel="RMSD"
              unit="nm"
              xData={rmsdRes.data.time_ps}
              yData={rmsdRes.data.rmsd_nm}
              csvDownloadUrl={getExportCsvUrl(jobId, 'rmsd')}
            />
          )}
        </div>
      )}

      {/* TAB CONTENT: RMSF */}
      {activeTab === 'rmsf' && (
        <div className="space-y-4">
          {!rmsfRes?.data?.rmsf_nm ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-3">
              <h3 className="text-sm font-bold text-slate-200">Root Mean Square Fluctuation (RMSF)</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Quantifies atomic fluctuations per residue along the protein backbone, distinguishing rigid secondary structure elements from flexible loops.
              </p>
              <button
                onClick={() => handleRunAnalysis('rmsf', { atom_selection: 'name CA' })}
                disabled={computingType === 'rmsf'}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow transition disabled:opacity-50"
              >
                {computingType === 'rmsf' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {computingType === 'rmsf' ? 'Computing Residue RMSF...' : 'Compute Residue RMSF'}
              </button>
            </div>
          ) : (
            <ScientificPlot
              title="Per-Residue C-alpha RMSF Profile"
              description="High peaks indicate flexible loop regions or terminal residues; low troughs indicate stable core motifs."
              xLabel="Residue Index"
              yLabel="RMSF"
              unit="nm"
              xData={rmsfRes.data.residue_indices}
              yData={rmsfRes.data.rmsf_nm}
              csvDownloadUrl={getExportCsvUrl(jobId, 'rmsf')}
            />
          )}
        </div>
      )}

      {/* TAB CONTENT: Radius of Gyration */}
      {activeTab === 'rg' && (
        <div className="space-y-4">
          {!rgRes?.data?.rg_nm ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-3">
              <h3 className="text-sm font-bold text-slate-200">Radius of Gyration (Rg)</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Tracks global compactness and folding stability of the macromolecular complex.
              </p>
              <button
                onClick={() => handleRunAnalysis('radius_of_gyration')}
                disabled={computingType === 'radius_of_gyration'}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow transition disabled:opacity-50"
              >
                {computingType === 'radius_of_gyration' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {computingType === 'radius_of_gyration' ? 'Computing Rg...' : 'Compute Radius of Gyration'}
              </button>
            </div>
          ) : (
            <ScientificPlot
              title="Radius of Gyration (Rg) vs Time"
              description="A steady, low Rg indicates a stably folded biomolecular architecture throughout the simulation."
              xLabel="Time (ps)"
              yLabel="Radius of Gyration"
              unit="nm"
              xData={rgRes.data.time_ps}
              yData={rgRes.data.rg_nm}
              csvDownloadUrl={getExportCsvUrl(jobId, 'radius_of_gyration')}
            />
          )}
        </div>
      )}

      {/* TAB CONTENT: SASA */}
      {activeTab === 'sasa' && (
        <div className="space-y-4">
          {!sasaRes?.data?.total_sasa_nm2 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-3">
              <h3 className="text-sm font-bold text-slate-200">Solvent Accessible Surface Area (SASA)</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Computes solvent accessibility using the Shrake-Rupley numerical algorithm with a 1.4 Å water probe radius.
              </p>
              <button
                onClick={() => handleRunAnalysis('sasa', { mode: 'both' })}
                disabled={computingType === 'sasa'}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow transition disabled:opacity-50"
              >
                {computingType === 'sasa' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {computingType === 'sasa' ? 'Computing SASA...' : 'Compute SASA'}
              </button>
            </div>
          ) : (
            <ScientificPlot
              title="Total Solvent Accessible Surface Area (SASA) vs Time"
              description="Reflects changes in solvent exposure upon ligand binding or conformational shifts."
              xLabel="Time (ps)"
              yLabel="Total SASA"
              unit="nm²"
              xData={sasaRes.data.time_ps}
              yData={sasaRes.data.total_sasa_nm2}
              csvDownloadUrl={getExportCsvUrl(jobId, 'sasa')}
            />
          )}
        </div>
      )}

      {/* TAB CONTENT: Hydrogen Bonds */}
      {activeTab === 'hbonds' && (
        <div className="space-y-4">
          {!hbondsRes?.data?.n_hbonds_per_frame ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-3">
              <h3 className="text-sm font-bold text-slate-200">Hydrogen Bond Dynamics & Occupancy</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Identifies intra- and intermolecular H-bonds using geometric criteria (distance ≤ 0.35 nm, angle ≥ 150°).
              </p>
              <button
                onClick={() => handleRunAnalysis('hydrogen_bonds')}
                disabled={computingType === 'hydrogen_bonds'}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow transition disabled:opacity-50"
              >
                {computingType === 'hydrogen_bonds' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {computingType === 'hydrogen_bonds' ? 'Analyzing H-Bonds...' : 'Analyze Hydrogen Bonds'}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <ScientificPlot
                title="Total Hydrogen Bonds Count vs Time"
                description="Tracks the stability of the hydrogen bonding network throughout the simulation."
                xLabel="Time (ps)"
                yLabel="Number of H-Bonds"
                xData={hbondsRes.data.time_ps}
                yData={hbondsRes.data.n_hbonds_per_frame}
                csvDownloadUrl={getExportCsvUrl(jobId, 'hydrogen_bonds')}
              />

              {/* H-Bond Occupancy Table */}
              {hbondsRes.data.hbond_details?.length > 0 && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                    <Table className="w-4 h-4 text-teal-400" /> Top Persistent Hydrogen Bonds
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="p-2.5">Donor Residue</th>
                          <th className="p-2.5">Hydrogen Atom</th>
                          <th className="p-2.5">Acceptor Residue</th>
                          <th className="p-2.5">Occupancy (%)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 text-slate-200">
                        {hbondsRes.data.hbond_details.slice(0, 10).map((hb: any, idx: number) => (
                          <tr key={idx} className="hover:bg-slate-850/60 transition">
                            <td className="p-2.5 text-teal-400">{hb.donor}</td>
                            <td className="p-2.5 text-slate-400">{hb.hydrogen}</td>
                            <td className="p-2.5 text-amber-400">{hb.acceptor}</td>
                            <td className="p-2.5 font-bold text-white">{(hb.occupancy * 100).toFixed(1)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: PCA */}
      {activeTab === 'pca' && (
        <div className="space-y-4">
          {!pcaRes?.data?.projections_pc1 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-3">
              <h3 className="text-sm font-bold text-slate-200">Principal Component Analysis (Essential Dynamics)</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Constructs covariance matrix from aligned coordinates to extract collective motions along principal modes.
              </p>
              <button
                onClick={() => handleRunAnalysis('pca', { atom_selection: 'name CA' })}
                disabled={computingType === 'pca'}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow transition disabled:opacity-50"
              >
                {computingType === 'pca' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {computingType === 'pca' ? 'Computing PCA...' : 'Compute PCA Modes'}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <ScientificPlot
                title="Principal Component 1 (PC1) Projection vs Time"
                description={`PC1 captures ${pcaRes.data.explained_variance_pct?.[0]?.toFixed(1)}% of total conformational variance.`}
                xLabel="Time (ps)"
                yLabel="PC1 Projection (nm)"
                xData={pcaRes.data.time_ps}
                yData={pcaRes.data.projections_pc1}
                yDataSecondary={pcaRes.data.projections_pc2}
                secondaryLabel="PC2 Projection"
                csvDownloadUrl={getExportCsvUrl(jobId, 'pca')}
              />
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: Contact Map */}
      {activeTab === 'contacts' && (
        <div className="space-y-4">
          {!contactRes?.data?.contact_matrix ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-3">
              <h3 className="text-sm font-bold text-slate-200">Residue–Residue Contact Map</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Calculates the contact frequency between all residue pairs across all trajectory frames (cutoff = 0.45 nm).
              </p>
              <button
                onClick={() => handleRunAnalysis('contact_map', { cutoff: 0.45 })}
                disabled={computingType === 'contact_map'}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs shadow transition disabled:opacity-50"
              >
                {computingType === 'contact_map' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {computingType === 'contact_map' ? 'Generating Contact Map...' : 'Generate Contact Map'}
              </button>
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Residue Contact Frequency Heatmap</h3>
                  <p className="text-xs text-slate-400">
                    Matrix dimension: {contactRes.data.contact_matrix.length} × {contactRes.data.contact_matrix.length} residues.
                  </p>
                </div>
                <a
                  href={getExportCsvUrl(jobId, 'contact_map')}
                  download
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-teal-400 border border-slate-700 font-medium transition"
                >
                  <Download className="w-3.5 h-3.5" /> Export Matrix CSV
                </a>
              </div>

              {/* 2D Matrix Rendering */}
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 overflow-auto max-h-96">
                <div
                  className="grid gap-[1px]"
                  style={{
                    gridTemplateColumns: `repeat(${contactRes.data.contact_matrix.length}, minmax(4px, 1fr))`,
                  }}
                >
                  {contactRes.data.contact_matrix.map((row: number[], i: number) =>
                    row.map((val: number, j: number) => (
                      <div
                        key={`${i}-${j}`}
                        title={`Residue ${i + 1} ↔ ${j + 1}: ${(val * 100).toFixed(0)}% contact`}
                        className="aspect-square transition-all hover:scale-125"
                        style={{
                          backgroundColor:
                            val > 0.8
                              ? '#14b8a6'
                              : val > 0.5
                              ? '#0d9488'
                              : val > 0.2
                              ? '#115e59'
                              : val > 0.05
                              ? '#134e4a'
                              : '#020617',
                        }}
                      />
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
