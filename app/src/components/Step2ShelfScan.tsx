import React, { useState } from 'react';
import { ScanResult, ShelfItem } from '../types';
import { Camera, RefreshCw } from 'lucide-react';

interface Step2ShelfScanProps {
  scan: ScanResult;
  hoveredItemId: string | null;
  onHoverItem: (id: string | null) => void;
  onSelectItem: (item: ShelfItem) => void;
  isScanning: boolean;
  scanStep: number;
  onTriggerScan: () => void;
}

export const Step2ShelfScan: React.FC<Step2ShelfScanProps> = ({
  scan,
  hoveredItemId,
  onHoverItem,
  onSelectItem,
  isScanning,
  scanStep,
  onTriggerScan,
}) => {
  const [outlineFilter, setOutlineFilter] = useState<'all' | 'issues' | 'none'>('all');
  const [activeTooltip, setActiveTooltip] = useState<ShelfItem | null>(null);

  const steps = [
    { title: 'Uploading shelf image', desc: 'Preparing high-resolution photo' },
    { title: 'Reading book spines', desc: 'Claude Opus 5.5 (high effort)' },
    { title: 'Zoom & verify pass', desc: 'Re-inspecting crowded sections' },
    { title: 'Comparing to planogram', desc: 'Matching titles against bay catalogue' },
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex flex-col h-full">
      {/* Step Header */}
      <div className="p-4 border-b border-slate-100 bg-slate-50/70">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
              2
            </span>
            <h2 className="text-sm font-bold text-slate-900 tracking-tight">Shelf Photo &amp; AI Recognition</h2>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={onTriggerScan}
              disabled={isScanning}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-xs transition-all ${
                isScanning
                  ? 'bg-blue-100 text-blue-700 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-98'
              }`}
            >
              {isScanning ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Scanning...</span>
                </>
              ) : (
                <>
                  <Camera className="w-3.5 h-3.5" />
                  <span>Scan Shelf</span>
                </>
              )}
            </button>
          </div>
        </div>
        <p className="text-xs text-slate-500">
          Real shelf photograph scanned by Claude Opus 5.5. AI detects spines and cross-references them against the planogram.
        </p>

        {/* Scan Status Summary Bar */}
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-200/60 text-xs">
          <div className="flex items-center space-x-3">
            <span className="text-slate-600 font-medium">
              Detected: <strong className="text-slate-900 font-bold">{scan.shelf_items.length} books</strong>
            </span>
            <span className="text-slate-300">|</span>
            <span className="text-emerald-700 font-medium">
              Matched: <strong>{scan.metrics.matched_count}</strong>
            </span>
            <span className="text-slate-300">|</span>
            <span className="text-amber-700 font-medium">
              Misplaced: <strong>{scan.metrics.misplaced_count}</strong>
            </span>
          </div>

          <div className="flex items-center space-x-1">
            <span className="text-slate-400 text-[11px] mr-1">Outlines:</span>
            <button
              onClick={() => setOutlineFilter('all')}
              className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                outlineFilter === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setOutlineFilter('issues')}
              className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                outlineFilter === 'issues'
                  ? 'bg-amber-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Issues Only
            </button>
            <button
              onClick={() => setOutlineFilter('none')}
              className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                outlineFilter === 'none'
                  ? 'bg-slate-800 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              Off
            </button>
          </div>
        </div>
      </div>

      {/* Main Image View Area */}
      <div className="relative flex-1 bg-slate-900 flex items-center justify-center overflow-hidden min-h-[380px] select-none">
        {/* Scanning Overlay Animation */}
        {isScanning && (
          <div className="absolute inset-0 bg-slate-950/85 backdrop-blur-xs z-20 flex flex-col items-center justify-center p-6 text-white text-center">
            <div className="w-12 h-12 rounded-full border-3 border-blue-500 border-t-transparent animate-spin mb-4" />
            <div className="text-sm font-bold text-white mb-1">
              Step {scanStep + 1} of 4: {steps[scanStep].title}
            </div>
            <p className="text-xs text-blue-200 mb-6">{steps[scanStep].desc}</p>
            <div className="w-64 bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-blue-500 h-full transition-all duration-300"
                style={{ width: `${((scanStep + 1) / 4) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Shelf Photo Container tightly hugging image */}
        <div className="relative inline-block max-h-[520px] max-w-full my-auto">
          <img
            src={scan.photo_url}
            alt={scan.bay_name}
            className="max-h-[520px] max-w-full w-auto h-auto object-contain block mx-auto rounded-sm"
          />

          {/* Interactive Bounding Outlines Overlay */}
          {outlineFilter !== 'none' && !isScanning && (
            <div className="absolute inset-0 pointer-events-auto">
              {scan.shelf_items.map((item) => {
                const isHovered = hoveredItemId === item.id;
                const isMisplaced = item.status === 'misplaced';
                const isUnexpected = item.status === 'unexpected';

                // Skip healthy items if 'issues' only filter is selected
                if (outlineFilter === 'issues' && !isMisplaced && !isUnexpected) {
                  return null;
                }

                // Styling based on planogram match status
                let borderClass = 'border-emerald-400 bg-emerald-500/15 hover:bg-emerald-500/30';

                if (isMisplaced) {
                  borderClass = 'border-amber-400 bg-amber-500/25 hover:bg-amber-500/40 ring-2 ring-amber-300/60 animate-pulse';
                } else if (isUnexpected) {
                  borderClass = 'border-purple-400 bg-purple-500/20 hover:bg-purple-500/35';
                }

                if (isHovered) {
                  borderClass += ' ring-3 ring-blue-400 z-10 scale-[1.02] shadow-lg';
                }

                return (
                  <div
                    key={item.id}
                    onMouseEnter={() => {
                      onHoverItem(item.id);
                      setActiveTooltip(item);
                    }}
                    onMouseLeave={() => {
                      onHoverItem(null);
                      setActiveTooltip(null);
                    }}
                    onClick={() => onSelectItem(item)}
                    style={{
                      top: `${item.box.top * 100}%`,
                      left: `${item.box.left * 100}%`,
                      width: `${item.box.width * 100}%`,
                      height: `${item.box.height * 100}%`,
                    }}
                    className={`absolute cursor-pointer border-2 rounded-xs transition-all duration-150 ${borderClass}`}
                  >
                    {isMisplaced && (
                      <div className="absolute -top-3 left-0 px-1 py-0.2 rounded text-[9px] font-bold bg-amber-600 text-white shadow-xs whitespace-nowrap">
                        Misplaced
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Active Hover Detail Card */}
          {activeTooltip && (
            <div
              className="absolute z-30 bottom-3 left-3 right-3 bg-slate-900/95 text-white p-3 rounded-lg border border-slate-700 shadow-xl backdrop-blur-md pointer-events-none max-w-md mx-auto"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span
                    className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase mb-1 ${
                      activeTooltip.status === 'matched'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        : activeTooltip.status === 'misplaced'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        : 'bg-purple-500/20 text-purple-300 border border-purple-500/40'
                    }`}
                  >
                    {activeTooltip.status_label}
                  </span>
                  <div className="text-xs font-bold text-white line-clamp-1">{activeTooltip.title}</div>
                  <div className="text-[11px] text-slate-300 line-clamp-1">{activeTooltip.author || 'Author unspecified'}</div>
                  {activeTooltip.misplaced_reason && (
                    <div className="text-[11px] text-amber-300 font-semibold mt-1">
                      ⚠️ {activeTooltip.misplaced_reason}
                    </div>
                  )}
                </div>
                <div className="text-right pl-3 shrink-0">
                  <div className="text-[10px] text-slate-400">Confidence</div>
                  <div className="text-xs font-mono font-bold text-emerald-400">
                    {(activeTooltip.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-2.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500">
        <span>Photo: {scan.photo_filename} · Approx spine outlines</span>
        <span>Latency: {scan.inference_duration_seconds}s · Cost: ${scan.estimated_cost_usd}</span>
      </div>
    </div>
  );
};
