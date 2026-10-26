import React from 'react';
import { Sparkles, RotateCcw, Info, Layers } from 'lucide-react';
import { Bay } from '../types';

interface HeaderProps {
  bays: Bay[];
  selectedBayId: string;
  onSelectBay: (id: string) => void;
  onReset: () => void;
  onOpenInfo: () => void;
  modelName: string;
}

export const Header: React.FC<HeaderProps> = ({
  bays,
  selectedBayId,
  onSelectBay,
  onReset,
  onOpenInfo,
  modelName,
}) => {
  const scannableBays = bays.filter((b) => b.scannable);

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Product Title */}
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-xs">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg text-slate-900 tracking-tight">Shelf Check</span>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                  Demo
                </span>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200/80">
                  Simulated store data
                </span>
              </div>
              <p className="text-xs text-slate-500">
                In-Store AI Shelf Scanning & Planogram Verification · Straive Innovation
              </p>
            </div>
          </div>

          {/* Bay Selector & Controls */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 bg-slate-50 border border-slate-200 rounded-lg p-1">
              <span className="text-xs font-medium text-slate-500 pl-2">Shelf Bay:</span>
              <select
                value={selectedBayId}
                onChange={(e) => onSelectBay(e.target.value)}
                className="bg-white text-xs font-semibold text-slate-800 border border-slate-200 rounded-md py-1.5 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {scannableBays.map((bay) => (
                  <option key={bay.id} value={bay.id}>
                    {bay.name} {bay.open_exceptions ? `(${bay.open_exceptions} alerts)` : '✓'}
                  </option>
                ))}
              </select>
            </div>

            {/* Model Badge */}
            <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-xs font-medium text-slate-700">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              <span>{modelName}</span>
              <span className="text-slate-400">·</span>
              <span className="text-emerald-700 font-medium">Replay (Offline)</span>
            </div>

            {/* Info & Reset */}
            <button
              onClick={onOpenInfo}
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
              title="About AI Model & Accuracy Benchmark"
            >
              <Info className="w-4 h-4" />
            </button>

            <button
              onClick={onReset}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors shadow-2xs"
              title="Reset all resolved tasks and simulated inventory"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Reset Demo</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
