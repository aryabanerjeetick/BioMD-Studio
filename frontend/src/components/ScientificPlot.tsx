import React, { useState, useMemo } from 'react';
import { Download, ZoomIn, ZoomOut, RotateCcw, Info } from 'lucide-react';

interface ScientificPlotProps {
  title: string;
  xLabel: string;
  yLabel: string;
  xData: number[];
  yData: number[];
  yDataSecondary?: number[];
  secondaryLabel?: string;
  unit?: string;
  height?: number;
  csvDownloadUrl?: string;
  description?: string;
}

export const ScientificPlot: React.FC<ScientificPlotProps> = ({
  title,
  xLabel,
  yLabel,
  xData,
  yData,
  yDataSecondary,
  secondaryLabel,
  unit = '',
  height = 300,
  csvDownloadUrl,
  description,
}) => {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  // Compute Statistics
  const stats = useMemo(() => {
    if (!yData || yData.length === 0) return null;
    const n = yData.length;
    let min = Infinity;
    let max = -Infinity;
    let sum = 0;
    for (let i = 0; i < n; i++) {
      const v = yData[i];
      if (v < min) min = v;
      if (v > max) max = v;
      sum += v;
    }
    const mean = sum / n;
    let varianceSum = 0;
    for (let i = 0; i < n; i++) {
      varianceSum += Math.pow(yData[i] - mean, 2);
    }
    const std = Math.sqrt(varianceSum / n);
    return { min, max, mean, std, n };
  }, [yData]);

  if (!xData || !yData || xData.length === 0 || yData.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-500">
        <p className="text-sm">No computed data points available for this observable.</p>
        <p className="text-xs text-slate-600 mt-1">Status: Not calculated or pending simulation trajectory.</p>
      </div>
    );
  }

  // Plot layout calculations
  const padding = { top: 30, right: 30, bottom: 50, left: 65 };
  const width = 640; // SVG viewBox width

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const minX = Math.min(...xData);
  const maxX = Math.max(...xData);
  const allY = yDataSecondary ? [...yData, ...yDataSecondary] : yData;
  const minY = Math.min(...allY);
  const maxY = Math.max(...allY);

  const rangeX = maxX - minX || 1;
  const rangeY = (maxY - minY) || 1;

  // Add 5% padding to Y range
  const yBuffer = rangeY * 0.05;
  const plotMinY = minY - yBuffer;
  const plotMaxY = maxY + yBuffer;
  const effectiveRangeY = plotMaxY - plotMinY;

  const scaleX = (x: number) => padding.left + ((x - minX) / rangeX) * plotWidth;
  const scaleY = (y: number) => padding.top + plotHeight - ((y - plotMinY) / effectiveRangeY) * plotHeight;

  // Build SVG path strings
  const primaryPath = useMemo(() => {
    return xData.map((x, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(x).toFixed(1)} ${scaleY(yData[i]).toFixed(1)}`).join(' ');
  }, [xData, yData, scaleX, scaleY]);

  const secondaryPath = useMemo(() => {
    if (!yDataSecondary) return null;
    return xData.map((x, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(x).toFixed(1)} ${scaleY(yDataSecondary[i]).toFixed(1)}`).join(' ');
  }, [xData, yDataSecondary, scaleX, scaleY]);

  // Generate nice tick marks for Y axis
  const yTicks = useMemo(() => {
    const ticks = [];
    const count = 5;
    for (let i = 0; i <= count; i++) {
      const val = plotMinY + (effectiveRangeY / count) * i;
      ticks.push({ val, y: scaleY(val) });
    }
    return ticks;
  }, [plotMinY, effectiveRangeY, scaleY]);

  // Generate tick marks for X axis
  const xTicks = useMemo(() => {
    const ticks = [];
    const count = 5;
    for (let i = 0; i <= count; i++) {
      const val = minX + (rangeX / count) * i;
      ticks.push({ val, x: scaleX(val) });
    }
    return ticks;
  }, [minX, rangeX, scaleX]);

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const svgX = ((e.clientX - rect.left) / rect.width) * width;
    if (svgX < padding.left || svgX > width - padding.right) {
      setHoverIndex(null);
      return;
    }
    const ratio = (svgX - padding.left) / plotWidth;
    const targetX = minX + ratio * rangeX;

    // Find closest index in xData
    let closestIdx = 0;
    let closestDist = Infinity;
    for (let i = 0; i < xData.length; i++) {
      const d = Math.abs(xData[i] - targetX);
      if (d < closestDist) {
        closestDist = d;
        closestIdx = i;
      }
    }
    setHoverIndex(closestIdx);
  };

  const handleMouseLeave = () => setHoverIndex(null);

  const downloadCSVLocal = () => {
    let csv = `${xLabel},${yLabel}${yDataSecondary ? ',' + secondaryLabel : ''}\n`;
    for (let i = 0; i < xData.length; i++) {
      csv += `${xData[i]},${yData[i]}${yDataSecondary ? ',' + yDataSecondary[i] : ''}\n`;
    }
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/\s+/g, '_')}_data.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
            {title}
            {unit && <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-teal-400 font-mono">[{unit}]</span>}
          </h3>
          {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {csvDownloadUrl ? (
            <a
              href={csvDownloadUrl}
              download
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-teal-400 border border-slate-700 font-medium transition"
            >
              <Download className="w-3.5 h-3.5" /> Export CSV
            </a>
          ) : (
            <button
              onClick={downloadCSVLocal}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-teal-400 border border-slate-700 font-medium transition"
            >
              <Download className="w-3.5 h-3.5" /> Export CSV
            </button>
          )}
        </div>
      </div>

      {/* Statistical Summary Pills */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 text-xs">
          <div>
            <span className="text-slate-500">Mean:</span>{' '}
            <span className="font-mono font-semibold text-slate-200">
              {stats.mean.toFixed(3)} {unit}
            </span>
          </div>
          <div>
            <span className="text-slate-500">Std Dev:</span>{' '}
            <span className="font-mono font-semibold text-slate-200">
              ±{stats.std.toFixed(3)} {unit}
            </span>
          </div>
          <div>
            <span className="text-slate-500">Min:</span>{' '}
            <span className="font-mono text-emerald-400">{stats.min.toFixed(3)}</span>
          </div>
          <div>
            <span className="text-slate-500">Max:</span>{' '}
            <span className="font-mono text-amber-400">{stats.max.toFixed(3)}</span>
          </div>
        </div>
      )}

      {/* SVG Canvas */}
      <div className="relative w-full overflow-hidden bg-slate-950 rounded-lg border border-slate-800/80">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto cursor-crosshair select-none"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          {/* Grid lines */}
          {yTicks.map((t, idx) => (
            <line
              key={`y-grid-${idx}`}
              x1={padding.left}
              y1={t.y}
              x2={width - padding.right}
              y2={t.y}
              stroke="#1e293b"
              strokeDasharray="3 3"
            />
          ))}
          {xTicks.map((t, idx) => (
            <line
              key={`x-grid-${idx}`}
              x1={t.x}
              y1={padding.top}
              x2={t.x}
              y2={height - padding.bottom}
              stroke="#1e293b"
              strokeDasharray="3 3"
            />
          ))}

          {/* Axes */}
          <line
            x1={padding.left}
            y1={height - padding.bottom}
            x2={width - padding.right}
            y2={height - padding.bottom}
            stroke="#475569"
            strokeWidth="1.5"
          />
          <line
            x1={padding.left}
            y1={padding.top}
            x2={padding.left}
            y2={height - padding.bottom}
            stroke="#475569"
            strokeWidth="1.5"
          />

          {/* X Ticks & Labels */}
          {xTicks.map((t, idx) => (
            <g key={`x-tick-${idx}`}>
              <line x1={t.x} y1={height - padding.bottom} x2={t.x} y2={height - padding.bottom + 5} stroke="#64748b" />
              <text
                x={t.x}
                y={height - padding.bottom + 18}
                textAnchor="middle"
                fill="#94a3b8"
                fontSize="10"
                fontFamily="monospace"
              >
                {t.val.toFixed(1)}
              </text>
            </g>
          ))}

          {/* Y Ticks & Labels */}
          {yTicks.map((t, idx) => (
            <g key={`y-tick-${idx}`}>
              <line x1={padding.left - 5} y1={t.y} x2={padding.left} y2={t.y} stroke="#64748b" />
              <text
                x={padding.left - 8}
                y={t.y + 3}
                textAnchor="end"
                fill="#94a3b8"
                fontSize="10"
                fontFamily="monospace"
              >
                {t.val.toFixed(2)}
              </text>
            </g>
          ))}

          {/* Axis Titles */}
          <text
            x={padding.left + plotWidth / 2}
            y={height - 8}
            textAnchor="middle"
            fill="#cbd5e1"
            fontSize="11"
            fontWeight="600"
          >
            {xLabel}
          </text>
          <text
            transform={`rotate(-90)`}
            x={-(padding.top + plotHeight / 2)}
            y={18}
            textAnchor="middle"
            fill="#cbd5e1"
            fontSize="11"
            fontWeight="600"
          >
            {yLabel} {unit ? `(${unit})` : ''}
          </text>

          {/* Secondary Line (if present) */}
          {secondaryPath && (
            <path d={secondaryPath} fill="none" stroke="#f59e0b" strokeWidth="1.5" strokeOpacity="0.85" />
          )}

          {/* Primary Line */}
          <path d={primaryPath} fill="none" stroke="#14b8a6" strokeWidth="1.8" />

          {/* Hover Crosshair & Indicator */}
          {hoverIndex !== null && (
            <g>
              <line
                x1={scaleX(xData[hoverIndex])}
                y1={padding.top}
                x2={scaleX(xData[hoverIndex])}
                y2={height - padding.bottom}
                stroke="#38bdf8"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              <circle
                cx={scaleX(xData[hoverIndex])}
                cy={scaleY(yData[hoverIndex])}
                r="4.5"
                fill="#14b8a6"
                stroke="#ffffff"
                strokeWidth="2"
              />
            </g>
          )}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoverIndex !== null && (
          <div
            className="absolute top-2 right-3 bg-slate-900/95 border border-teal-500/50 rounded px-2.5 py-1.5 text-xs shadow-xl pointer-events-none backdrop-blur"
          >
            <div className="font-mono text-slate-300">
              {xLabel}: <span className="font-semibold text-white">{xData[hoverIndex].toFixed(2)}</span>
            </div>
            <div className="font-mono text-teal-400 font-semibold">
              {yLabel}: {yData[hoverIndex].toFixed(4)} {unit}
            </div>
          </div>
        )}
      </div>

      {/* Legend if secondary data present */}
      {yDataSecondary && (
        <div className="flex items-center gap-4 mt-3 text-xs justify-center">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-teal-500 rounded"></span>
            <span className="text-slate-300 font-medium">Primary: {yLabel}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-amber-500 rounded"></span>
            <span className="text-slate-300 font-medium">{secondaryLabel || 'Secondary'}</span>
          </div>
        </div>
      )}
    </div>
  );
};
