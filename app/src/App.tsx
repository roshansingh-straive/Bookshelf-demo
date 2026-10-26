import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Step1Planogram } from './components/Step1Planogram';
import { Step2ShelfScan } from './components/Step2ShelfScan';
import { Step3DiscrepancyView } from './components/Step3DiscrepancyView';
import { TrustModal } from './components/TrustModal';
import { StoreData, ScanResult, ShelfItem } from './types';
import { ShieldCheck } from 'lucide-react';

export const App: React.FC = () => {
  const [storeData, setStoreData] = useState<StoreData | null>(null);
  const [selectedBayId, setSelectedBayId] = useState<string>('bay_f3');
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [scanStep, setScanStep] = useState<number>(0);
  const [hoveredItemId, setHoveredItemId] = useState<string | null>(null);
  const [highlightedSku, setHighlightedSku] = useState<string | null>(null);
  const [isTrustOpen, setIsTrustOpen] = useState<boolean>(false);
  const [resolvedTaskIds, setResolvedTaskIds] = useState<Set<string>>(new Set());

  // Load initial store data
  useEffect(() => {
    fetch('/data/store.json')
      .then((res) => res.json())
      .then((data: StoreData) => {
        setStoreData(data);
      })
      .catch((err) => console.error('Failed to load store data:', err));
  }, []);

  // Load scan result whenever selected bay changes
  useEffect(() => {
    if (!selectedBayId) return;
    fetch(`/data/scans/${selectedBayId}.json`)
      .then((res) => res.json())
      .then((data: ScanResult) => {
        setScanResult(data);
      })
      .catch((err) => console.error('Failed to load scan data:', err));
  }, [selectedBayId]);

  // Trigger simulated scan sequence
  const handleTriggerScan = () => {
    if (isScanning) return;
    setIsScanning(true);
    setScanStep(0);

    const stepInterval = setInterval(() => {
      setScanStep((prev) => {
        if (prev >= 3) {
          clearInterval(stepInterval);
          setIsScanning(false);
          return 0;
        }
        return prev + 1;
      });
    }, 700);
  };

  // Resolve an action task (human in the loop)
  const handleResolveTask = (taskId: string) => {
    setResolvedTaskIds((prev) => {
      const next = new Set(prev);
      next.add(taskId);
      return next;
    });
  };

  // Reset entire demo
  const handleReset = () => {
    setResolvedTaskIds(new Set());
    setHoveredItemId(null);
    setHighlightedSku(null);
    if (selectedBayId) {
      fetch(`/data/scans/${selectedBayId}.json`)
        .then((res) => res.json())
        .then((data: ScanResult) => setScanResult(data));
    }
  };

  if (!storeData || !scanResult) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-slate-500 text-xs">
        <div className="w-8 h-8 rounded-full border-2 border-blue-600 border-t-transparent animate-spin mb-3" />
        <span>Loading Shelf Check demo...</span>
      </div>
    );
  }

  const selectedBay = storeData.bays.find((b) => b.id === selectedBayId) || storeData.bays[0];

  // Annotate tasks with resolution state
  const activeTasks = scanResult.action_tasks.map((t) => ({
    ...t,
    resolved: resolvedTaskIds.has(t.id),
  }));

  return (
    <div className="min-h-screen bg-slate-100/70 flex flex-col font-sans">
      {/* Top Navigation */}
      <Header
        bays={storeData.bays}
        selectedBayId={selectedBayId}
        onSelectBay={(id) => {
          setSelectedBayId(id);
          setResolvedTaskIds(new Set());
        }}
        onReset={handleReset}
        onOpenInfo={() => setIsTrustOpen(true)}
        modelName="Claude Opus 5.5"
      />

      {/* Main 3-Step Content Layout */}
      <main className="flex-1 max-w-[1700px] w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col">
        {/* Workflow Title & Context Bar */}
        <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
              <span>{selectedBay.name}</span>
              <span className="text-sm font-normal text-slate-400">·</span>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800 border border-blue-200">
                Aisle {selectedBay.aisle}
              </span>
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Three-step shelf verification: Compare the approved planogram with real shelf vision to flag missing and misplaced inventory.
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs">
            <button
              onClick={() => setIsTrustOpen(true)}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 font-medium transition-colors shadow-2xs"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
              <span>Can we trust it? (Accuracy)</span>
            </button>
          </div>
        </div>

        {/* 3-Step Side-by-Side Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 flex-1 items-stretch">
          {/* Step 1: Shelf Planogram (3.5 cols) */}
          <div className="lg:col-span-3 xl:col-span-3 flex flex-col h-full">
            <Step1Planogram
              bay={selectedBay}
              items={scanResult.planogram_items}
              highlightedSku={highlightedSku}
              onSelectSku={(sku) => setHighlightedSku(sku)}
            />
          </div>

          {/* Step 2: Shelf Photo & AI Scan (5.5 cols) */}
          <div className="lg:col-span-5 xl:col-span-5 flex flex-col h-full">
            <Step2ShelfScan
              scan={scanResult}
              hoveredItemId={hoveredItemId}
              onHoverItem={(id) => setHoveredItemId(id)}
              onSelectItem={(item: ShelfItem) => {
                if (item.sku) setHighlightedSku(item.sku);
              }}
              isScanning={isScanning}
              scanStep={scanStep}
              onTriggerScan={handleTriggerScan}
            />
          </div>

          {/* Step 3: Discrepancy & Action Feed (3.5 cols) */}
          <div className="lg:col-span-4 xl:col-span-4 flex flex-col h-full">
            <Step3DiscrepancyView
              tasks={activeTasks}
              metrics={scanResult.metrics}
              onResolveTask={handleResolveTask}
              hoveredItemId={hoveredItemId}
              onHoverItem={(id) => setHoveredItemId(id)}
            />
          </div>
        </div>
      </main>

      {/* Global Footer */}
      <footer className="bg-white border-t border-slate-200 py-3 px-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            <span>Shelf Check Demo</span>
            <span className="mx-2 text-slate-300">·</span>
            <span className="text-slate-400">Simulated store data</span>
          </div>
          <div>
            <span>Shelf photographs and answer keys based on </span>
            <a
              href="https://github.com/atharva-729/bookshelf-benchmark"
              target="_blank"
              rel="noreferrer"
              className="font-medium text-blue-600 hover:underline"
            >
              Straive's Bookshelf Benchmark (by atharva-729)
            </a>
          </div>
        </div>
      </footer>

      {/* Trust & Methodology Modal */}
      <TrustModal isOpen={isTrustOpen} onClose={() => setIsTrustOpen(false)} />
    </div>
  );
};
