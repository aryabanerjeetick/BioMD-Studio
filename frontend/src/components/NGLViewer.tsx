import React, { useEffect, useRef, useState } from 'react';
import * as NGL from 'ngl';
import { Camera, Eye, RotateCw, Sparkles, Layers, RefreshCw } from 'lucide-react';

interface NGLViewerProps {
  structureUrl?: string;
  structureContent?: string;
  fileExt?: string;
  height?: string;
  onLoaded?: () => void;
}

export const NGLViewer: React.FC<NGLViewerProps> = ({
  structureUrl,
  structureContent,
  fileExt = 'pdb',
  height = '420px',
  onLoaded,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<any>(null);
  const compRef = useRef<any>(null);

  const [representation, setRepresentation] = useState<'cartoon' | 'licorice' | 'surface' | 'ball+stick'>('cartoon');
  const [colorScheme, setColorScheme] = useState<string>('residueindex');
  const [isSpinning, setIsSpinning] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize NGL Stage
  useEffect(() => {
    if (!containerRef.current) return;

    try {
      const stage = new NGL.Stage(containerRef.current, {
        backgroundColor: '#020617', // slate-950
        cameraType: 'perspective',
      });
      stageRef.current = stage;

      const handleResize = () => stage.handleResize();
      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        stage.dispose();
      };
    } catch (err: any) {
      setError(`Failed to initialize 3D viewer: ${err.message}`);
      setLoading(false);
    }
  }, []);

  // Load structure when URL or content changes
  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;

    if (!structureUrl && !structureContent) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    stage.removeAllComponents();

    let loadPromise: Promise<any>;

    if (structureContent) {
      const blob = new Blob([structureContent], { type: 'text/plain' });
      loadPromise = stage.loadFile(blob, { ext: fileExt });
    } else if (structureUrl) {
      loadPromise = stage.loadFile(structureUrl, { ext: fileExt });
    } else {
      setLoading(false);
      return;
    }

    loadPromise
      .then((component: any) => {
        compRef.current = component;
        updateRepresentation(component, representation, colorScheme);
        component.autoView();
        setLoading(false);
        if (onLoaded) onLoaded();
      })
      .catch((err: any) => {
        console.error('NGL Load Error:', err);
        setError(`Failed to load 3D structure: ${err.message || 'Check file format'}`);
        setLoading(false);
      });
  }, [structureUrl, structureContent, fileExt]);

  // Update visual representation
  const updateRepresentation = (component: any, repType: string, scheme: string) => {
    if (!component) return;
    component.removeAllRepresentations();

    if (repType === 'cartoon') {
      component.addRepresentation('cartoon', { colorScheme: scheme, quality: 'high' });
      // Add ligand as licorice
      component.addRepresentation('licorice', {
        sele: 'hetero and not (water or ion)',
        colorScheme: 'element',
        multipleBond: true,
      });
    } else if (repType === 'surface') {
      component.addRepresentation('surface', { colorScheme: scheme, opacity: 0.7, wireframe: false });
      component.addRepresentation('licorice', { sele: 'hetero and not (water or ion)', colorScheme: 'element' });
    } else if (repType === 'ball+stick') {
      component.addRepresentation('ball+stick', { colorScheme: scheme, quality: 'high' });
    } else {
      component.addRepresentation('licorice', { colorScheme: scheme, multipleBond: true });
    }

    // Add metals/ions as spheres
    component.addRepresentation('spacefill', { sele: 'ion', colorScheme: 'element', scale: 0.6 });
  };

  const handleRepChange = (newRep: any) => {
    setRepresentation(newRep);
    if (compRef.current) {
      updateRepresentation(compRef.current, newRep, colorScheme);
    }
  };

  const handleColorChange = (newColor: string) => {
    setColorScheme(newColor);
    if (compRef.current) {
      updateRepresentation(compRef.current, representation, newColor);
    }
  };

  const toggleSpin = () => {
    if (!stageRef.current) return;
    if (isSpinning) {
      stageRef.current.setSpin(false);
    } else {
      stageRef.current.setSpin([0, 1, 0], 0.01);
    }
    setIsSpinning(!isSpinning);
  };

  const resetView = () => {
    if (compRef.current) compRef.current.autoView();
  };

  const takeScreenshot = () => {
    if (!stageRef.current) return;
    stageRef.current.makeImage({ factor: 2, antialias: true, trim: false }).then((blob: Blob) => {
      NGL.download(blob, 'structure_3d.png');
    });
  };

  return (
    <div className="relative rounded-xl overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl flex flex-col">
      {/* Controls Bar */}
      <div className="bg-slate-900/90 backdrop-blur px-4 py-2 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2 z-10 text-xs">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-teal-400" />
          <span className="font-semibold text-slate-300">Style:</span>
          <select
            value={representation}
            onChange={(e) => handleRepChange(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 outline-none focus:border-teal-500"
          >
            <option value="cartoon">Cartoon (Ribbon)</option>
            <option value="surface">Molecular Surface</option>
            <option value="licorice">Sticks (Licorice)</option>
            <option value="ball+stick">Ball & Stick</option>
          </select>

          <span className="font-semibold text-slate-300 ml-2">Color:</span>
          <select
            value={colorScheme}
            onChange={(e) => handleColorChange(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 outline-none focus:border-teal-500"
          >
            <option value="residueindex">Residue Index (Rainbow)</option>
            <option value="chainid">By Chain</option>
            <option value="element">By Element</option>
            <option value="sstruc">Secondary Structure</option>
            <option value="hydrophobicity">Hydrophobicity</option>
            <option value="bfactor">B-Factor / pLDDT</option>
          </select>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={toggleSpin}
            title={isSpinning ? 'Stop Rotation' : 'Auto Rotate'}
            className={`p-1.5 rounded transition ${isSpinning ? 'bg-teal-600 text-white' : 'bg-slate-800 hover:bg-slate-700 text-slate-300'}`}
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={resetView}
            title="Reset Camera View"
            className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={takeScreenshot}
            title="Download High-Res PNG"
            className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1"
          >
            <Camera className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 3D Canvas Container */}
      <div
        ref={containerRef}
        style={{ width: '100%', height }}
        className="relative cursor-grab active:cursor-grabbing"
      >
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/70 z-20">
            <div className="flex items-center gap-3 text-teal-400">
              <RefreshCw className="w-6 h-6 animate-spin" />
              <span className="text-sm font-medium">Rendering 3D Structure...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/90 z-20 p-6 text-center">
            <div className="max-w-md text-red-400 text-sm">
              <p className="font-semibold mb-1">Visualization Notice</p>
              <p className="text-slate-400">{error}</p>
            </div>
          </div>
        )}
      </div>

      <div className="px-3 py-1 bg-slate-950 border-t border-slate-900 text-[11px] text-slate-500 flex justify-between items-center">
        <span>Left-click: Rotate • Right-click: Pan • Scroll: Zoom</span>
        <span className="flex items-center gap-1 text-teal-500/80">
          <Sparkles className="w-3 h-3" /> NGL WebGL Renderer
        </span>
      </div>
    </div>
  );
};
