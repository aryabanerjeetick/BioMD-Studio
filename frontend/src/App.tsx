import React, { useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { NewSimulation } from './pages/NewSimulation';
import { JobMonitor } from './pages/JobMonitor';
import { AnalysisDashboard } from './pages/AnalysisDashboard';
import { ProjectFiles } from './pages/ProjectFiles';
import { ColabGuide } from './pages/ColabGuide';
import { Docs } from './pages/Docs';
import { listProjects, getSystemStatus } from './api';
import { Project, SystemStatus } from './types';
import { Activity, ShieldCheck, Heart } from 'lucide-react';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Load projects & system status on mount
  const refreshData = async () => {
    try {
      const [pList, sys] = await Promise.all([
        listProjects().catch(() => []),
        getSystemStatus().catch(() => null),
      ]);
      setProjects(pList);
      setSystemStatus(sys);
      if (pList.length > 0 && !selectedProject) {
        setSelectedProject(pList[0]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshData();
  }, []);

  const handleSelectProject = (project: Project) => {
    setSelectedProject(project);
    setCurrentTab('new');
  };

  const handleJobStarted = (jobId: string, projectId: string) => {
    setActiveJobId(jobId);
    setCurrentTab('monitor');
    refreshData();
  };

  const handleOpenAnalysis = (jobId: string) => {
    setActiveJobId(jobId);
    setCurrentTab('analysis');
  };

  const handleOpenFiles = (jobId: string) => {
    setActiveJobId(jobId);
    setCurrentTab('files');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-slate-950">
      {/* Top Navigation */}
      <Navbar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        systemStatus={systemStatus}
        onRefreshStatus={refreshData}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentTab === 'dashboard' && (
          <Dashboard
            projects={projects}
            systemStatus={systemStatus}
            onSelectProject={handleSelectProject}
            onNewSimulation={() => setCurrentTab('new')}
            onOpenColabGuide={() => setCurrentTab('colab')}
          />
        )}

        {currentTab === 'new' && (
          <NewSimulation
            systemStatus={systemStatus}
            onJobStarted={handleJobStarted}
            onOpenColabGuide={() => setCurrentTab('colab')}
          />
        )}

        {currentTab === 'monitor' && (
          <JobMonitor
            jobId={activeJobId}
            onOpenAnalysis={handleOpenAnalysis}
            onOpenFiles={handleOpenFiles}
          />
        )}

        {currentTab === 'analysis' && (
          <AnalysisDashboard jobId={activeJobId} />
        )}

        {currentTab === 'files' && (
          <ProjectFiles jobId={activeJobId} />
        )}

        {currentTab === 'colab' && (
          <ColabGuide onRefreshStatus={refreshData} />
        )}

        {currentTab === 'docs' && (
          <Docs />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-6 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-teal-400" />
            <span>BioMD Studio • Built for Rigorous Computational Biophysics</span>
          </div>

          <div className="flex items-center gap-4 text-slate-400">
            <button onClick={() => setCurrentTab('docs')} className="hover:text-teal-400 transition">
              Citations & Methodology
            </button>
            <button onClick={() => setCurrentTab('colab')} className="hover:text-teal-400 transition">
              Free GPU Setup
            </button>
            <span>GROMACS • MDTraj • BioPython</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
export default App;
