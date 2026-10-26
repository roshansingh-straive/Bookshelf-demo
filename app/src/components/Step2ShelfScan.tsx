import React, { useEffect, useRef, useState } from 'react';
import { ScanProgress, ScanResult, ShelfItem } from '../types';
import { Camera, RefreshCw, ZoomIn, ZoomOut, X, Maximize2 } from 'lucide-react';

interface Step2ShelfScanProps {
  scan: ScanResult;
  mode: 'replay' | 'live';
  onModeChange: (mode: 'replay' | 'live') => void;
  liveAvailable: boolean;
  isUpload: boolean;
  resultReady: boolean;
  progress: ScanProgress | null;
  error: string | null;
  onCancel: () => void;
  hoveredItemId: string | null;
  onHoverItem: (id: string | null) => void;
  onSelectItem: (item: ShelfItem) => void;
  isScanning: boolean;
  scanStep: number;
  onTriggerScan: () => void;
}

export const Step2ShelfScan: React.FC<Step2ShelfScanProps> = ({
  scan, mode, onModeChange, liveAvailable, isUpload, resultReady, progress, error, onCancel,
  hoveredItemId, onHoverItem, onSelectItem, isScanning, scanStep, onTriggerScan,
}) => {
  const [outlineFilter, setOutlineFilter] = useState<'all' | 'issues' | 'none'>('none');
  const [activeTooltip, setActiveTooltip] = useState<ShelfItem | null>(null);
  const [photoOpen, setPhotoOpen] = useState(false);
  const [zoom, setZoom] = useState(1);
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    setActiveTooltip(null);
    setOutlineFilter(resultReady && scan.shelf_items.some(item => item.box) ? 'all' : 'none');
  }, [scan, resultReady]);

  useEffect(() => {
    if (photoOpen) dialog.current?.showModal();
    else dialog.current?.close();
  }, [photoOpen]);

  const selectItem = (item: ShelfItem) => {
    setActiveTooltip(item);
    onHoverItem(item.id);
    onSelectItem(item);
  };
  const verificationLabel = (item: ShelfItem) => item.verification_status === 'verified'
    ? 'Agreed across two readings' : item.verification_status === 'needs_review'
    ? 'Needs human review' : 'Saved benchmark reading';

  const outlines = () => outlineFilter !== 'none' && scan.shelf_items.map(item => {
    if (!item.box || (outlineFilter === 'issues' && item.status === 'matched')) return null;
    const colour = item.status === 'matched' ? 'border-emerald-400 bg-emerald-500/10'
      : item.status === 'misplaced' ? 'border-amber-400 bg-amber-500/20'
      : item.status === 'needs_review' ? 'border-rose-400 bg-rose-500/20'
      : 'border-purple-400 bg-purple-500/20';
    return <button
      key={item.id} aria-label={`${item.title}: ${item.status_label}`}
      onMouseEnter={() => { onHoverItem(item.id); setActiveTooltip(item); }}
      onMouseLeave={() => onHoverItem(null)}
      onFocus={() => { onHoverItem(item.id); setActiveTooltip(item); }}
      onClick={() => selectItem(item)}
      style={{ top: `${item.box.top * 100}%`, left: `${item.box.left * 100}%`, width: `${item.box.width * 100}%`, height: `${item.box.height * 100}%` }}
      className={`absolute cursor-pointer border-2 rounded-xs ${colour} ${hoveredItemId === item.id ? 'ring-2 ring-blue-400 z-10' : ''}`}
    />;
  });

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex flex-col h-full min-w-0">
      <div className="p-4 border-b border-slate-100 bg-slate-50/70">
        <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold">2</span>
            <h2 className="text-sm font-bold text-slate-900 tracking-tight">Shelf Photo &amp; AI Recognition</h2>
          </div>
          <button onClick={onTriggerScan} disabled={isScanning || (mode === 'live' && !liveAvailable)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-500 disabled:cursor-not-allowed">
            {isScanning ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Camera className="w-3.5 h-3.5" />}
            <span>{isScanning ? 'Analyzing…' : mode === 'live' ? (resultReady ? 'Analyze again' : 'Analyze photo') : 'Reload sample'}</span>
          </button>
        </div>
        {!isUpload && <div className="flex flex-wrap gap-2 items-center mb-2">
          <label className="text-xs text-slate-600 flex items-center gap-2">
            Scan mode
            <select aria-label="Scan mode" value={mode} disabled={isScanning} onChange={e => onModeChange(e.target.value as 'replay' | 'live')} className="text-xs border border-slate-300 rounded-md bg-white px-2 py-1.5">
              <option value="replay">Saved sample analysis</option>
              <option value="live" disabled={!liveAvailable}>Run a new analysis</option>
            </select>
          </label>
        </div>}
        <p className="text-xs text-slate-500 leading-relaxed">
          {mode === 'live'
            ? 'We read the photo section by section and cross-check titles in a second pass.'
            : 'This sample uses saved recognition results. Run a new analysis to inspect the sample photo again.'}
        </p>
        {!liveAvailable && !error && <p className="text-[11px] text-amber-800 mt-1">New photo analysis is currently unavailable on this server.</p>}
        {error && <div role="alert" className="mt-2 p-2 text-xs text-red-800 border border-red-200 bg-red-50 rounded-md">{error}</div>}
        <div className="mt-3 pt-3 border-t border-slate-200/60 text-xs space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-medium text-slate-700">{resultReady ? (isUpload ? 'Your photo · Analysis complete' : scan.mode === 'live' ? 'Sample · New analysis' : 'Sample · Saved analysis') : 'Your photo · Awaiting analysis'}</span>
            <span className="text-slate-500">{resultReady ? `${scan.shelf_items.length} unique titles` : 'Photo uploaded'}</span>
          </div>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="text-emerald-700">{resultReady ? <>Matched: {scan.metrics.matched_count} <span className="text-slate-400">· Review: {scan.metrics.review_count ?? 0}</span></> : <span className="text-slate-400">Results pending</span>}</span>
            <div className="flex items-center gap-1">
              <span className="text-slate-400 text-[11px]">Outlines:</span>
              {(['all', 'issues', 'none'] as const).map(filter => <button key={filter} disabled={filter !== 'none' && (!resultReady || !scan.shelf_items.some(item => item.box))} aria-pressed={outlineFilter === filter} onClick={() => setOutlineFilter(filter)} className={`px-2 py-0.5 rounded text-[11px] font-medium ${outlineFilter === filter ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed'}`}>{filter === 'all' ? 'All' : filter === 'issues' ? 'Issues' : 'Off'}</button>)}
            </div>
          </div>
        </div>
      </div>

      <div className="relative flex-1 bg-slate-900 flex items-center justify-center overflow-hidden min-h-[380px] select-none">
        <button aria-label="Open photo zoom" onClick={() => { setZoom(1); setPhotoOpen(true); }} className="absolute top-3 right-3 z-10 flex items-center gap-1.5 px-2.5 py-1.5 bg-white/95 rounded-lg text-xs font-medium text-slate-800 shadow-sm"><Maximize2 className="w-3.5 h-3.5" /> Zoom photo</button>
        <div className="relative inline-block max-h-[520px] max-w-full my-auto">
          <img src={scan.photo_url} alt={scan.bay_name} className="max-h-[520px] max-w-full w-auto h-auto object-contain block mx-auto" />
          {!isScanning && outlines()}
        </div>
        {isScanning && <div role="status" aria-live="polite" className="absolute inset-0 bg-slate-950/90 z-20 flex flex-col items-center justify-center p-6 text-white text-center">
          <RefreshCw className="w-10 h-10 text-blue-400 animate-spin mb-4" />
          <div className="text-sm font-bold mb-2">{mode === 'live' ? ['Preparing image', 'Reading full-resolution sections', 'Independent verification', 'Comparing planogram'][scanStep] : 'Loading saved reply'}</div>
          <p className="text-xs text-blue-200 max-w-xs mb-4">{scanStep === 0 ? 'Preparing your photo for a detailed reading.' : scanStep === 1 ? 'Reading visible titles across the shelf.' : scanStep === 2 ? 'Taking a second look at each section.' : 'Comparing recognized titles with the shelf planogram.'}</p>
          {!!progress?.total_calls && <><div className="text-xs mb-2">{progress.completed_calls} of {progress.total_calls} reading checks completed</div><progress className="w-64 max-w-full accent-blue-500" value={progress.completed_calls ?? 0} max={progress.total_calls} /></>}
          <p className="text-[11px] text-slate-400 mt-3">Detailed scans can take several minutes.</p>
          <button onClick={onCancel} className="mt-4 px-4 py-1.5 rounded border border-slate-500 text-xs">Cancel scan</button>
        </div>}
      </div>

      {activeTooltip && <div className="p-3 bg-blue-50 border-t border-blue-100 text-xs relative">
        <button onClick={() => { setActiveTooltip(null); onHoverItem(null); }} aria-label="Close title details" className="absolute top-2 right-2 p-1 text-slate-500"><X className="w-3.5 h-3.5" /></button>
        <div className="font-semibold text-slate-900 pr-6">{activeTooltip.title}</div>
        <div className="text-slate-600">{activeTooltip.author || 'Author unreadable / unspecified'}</div>
        <div className="text-blue-800 mt-1">{verificationLabel(activeTooltip)} · {activeTooltip.status_label}</div>
        {activeTooltip.visible_text && <div className="text-slate-600 mt-1">Visible text: “{activeTooltip.visible_text}”</div>}
        {activeTooltip.misplaced_reason && <div className="text-amber-800 mt-1">{activeTooltip.misplaced_reason}</div>}
      </div>}
      {resultReady && <details className="border-t border-slate-200 text-xs">
        <summary className="p-3 cursor-pointer font-medium text-slate-700">Inspect {scan.shelf_items.length} recognized titles</summary>
        <div className="max-h-48 overflow-y-auto divide-y divide-slate-100">
          {scan.shelf_items.map(item => <button key={item.id} onClick={() => selectItem(item)} className="block w-full text-left px-3 py-2 hover:bg-blue-50"><span className="font-medium text-slate-800">{item.title}</span><span className="block text-[11px] text-slate-500">{verificationLabel(item)}</span></button>)}
        </div>
      </details>}
      <div className="p-2.5 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500 space-y-1">
        <div className="break-words">{scan.photo_filename} · {resultReady ? (scan.mode === 'replay' ? 'Saved sample' : 'Estimated outlines; inspect the photo to confirm') : 'Uploaded photo'}</div>
        <div>{resultReady && scan.inference_duration_seconds != null ? `Analysis time: ${scan.inference_duration_seconds}s` : 'Review readings against the original photo before taking action.'}</div>
      </div>

      <dialog ref={dialog} onClose={() => setPhotoOpen(false)} aria-label="Full-resolution shelf photo" className="fixed inset-0 m-0 w-screen h-dvh max-w-none max-h-none bg-slate-950 text-white backdrop:bg-slate-950/90 p-0">
        <div className="flex items-center justify-between gap-2 p-4 border-b border-slate-700">
          <span className="text-sm font-semibold">{scan.bay_code} · Inspect shelf photo</span>
          <div className="flex items-center gap-2">
            <button aria-label="Zoom out" onClick={() => setZoom(z => Math.max(1, z - 0.5))} disabled={zoom <= 1} className="p-2 rounded bg-slate-800 disabled:opacity-30"><ZoomOut className="w-4 h-4" /></button>
            <span className="text-xs tabular-nums w-10 text-center">{zoom * 100}%</span>
            <button aria-label="Zoom in" onClick={() => setZoom(z => Math.min(4, z + 0.5))} disabled={zoom >= 4} className="p-2 rounded bg-slate-800 disabled:opacity-30"><ZoomIn className="w-4 h-4" /></button>
            <button aria-label="Close photo zoom" onClick={() => setPhotoOpen(false)} className="p-2 rounded bg-slate-800"><X className="w-4 h-4" /></button>
          </div>
        </div>
        <div className="overflow-auto h-[calc(100dvh-74px)]"><div className="relative" style={{ width: `${zoom * 100}%` }}><img src={scan.photo_url} alt={`Full-resolution ${scan.bay_name}`} className="w-full h-auto block" />{outlines()}</div></div>
      </dialog>
    </div>
  );
};
