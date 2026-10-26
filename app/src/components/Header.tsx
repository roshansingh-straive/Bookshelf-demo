import React from 'react';
import { ArrowLeft, Info, Layers, RotateCcw, ScanLine } from 'lucide-react';
import type { Bay } from '../types';

interface HeaderProps {
  bays: Bay[];
  selectedBayId: string;
  onSelectBay: (id: string) => void;
  onReset: () => void;
  onOpenInfo: () => void;
  onHome: () => void;
  isUpload: boolean;
  isScanning: boolean;
  resultMode: 'replay' | 'live';
}
export const Header: React.FC<HeaderProps> = ({ bays, selectedBayId, onSelectBay, onReset, onOpenInfo, onHome, isUpload, isScanning, resultMode }) => <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
  <div className="max-w-[1700px] mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-col xl:flex-row xl:items-center justify-between gap-3">
    <div className="flex items-center gap-3"><button onClick={onHome} aria-label="Go to homepage" className="w-9 h-9 rounded-xl bg-blue-600 text-white grid place-items-center shrink-0"><Layers className="w-5 h-5" /></button><div><span className="font-bold text-lg text-slate-900 tracking-tight">Shelf Check</span><p className="text-xs text-slate-500">Shelf analysis · Simulated store records</p></div></div>
    <div className="flex flex-wrap items-center gap-2 min-w-0">
      <div className="flex flex-1 min-w-0 items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg p-1"><span className="text-xs font-medium text-slate-500 pl-2 whitespace-nowrap">Shelf:</span><select aria-label="Shelf bay" value={selectedBayId} disabled={isUpload || isScanning} onChange={e => onSelectBay(e.target.value)} className="min-w-0 w-full sm:w-72 bg-white text-xs font-semibold text-slate-800 border border-slate-200 rounded-md py-1.5 px-3 disabled:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500">{bays.filter(bay => bay.scannable).map(bay => <option key={bay.id} value={bay.id}>{bay.name}</option>)}</select></div>
      <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-xs font-medium text-slate-600"><ScanLine className="w-3.5 h-3.5" />{isUpload ? 'Your shelf photo' : resultMode === 'live' ? 'New sample analysis' : 'Saved sample'}</span>
      <button onClick={onOpenInfo} aria-label="About recognition and accuracy" className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg"><Info className="w-4 h-4" /></button>
      {!isUpload && <button onClick={onReset} disabled={isScanning} aria-label="Reset sample" className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg disabled:opacity-40"><RotateCcw className="w-4 h-4" /></button>}
      <button onClick={onHome} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 border border-slate-200 hover:bg-slate-50 rounded-lg"><ArrowLeft className="w-3.5 h-3.5" /><span>Upload a photo</span></button>
    </div>
  </div>
</header>;
