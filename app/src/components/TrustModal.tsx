import React from 'react';
import { X, ShieldCheck, Sparkles } from 'lucide-react';

interface TrustModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const TrustModal: React.FC<TrustModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl max-w-xl w-full border border-slate-200 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-sm">How AI Shelf Scanning Works</h3>
              <p className="text-xs text-slate-500">Methodology, verification, and benchmark accuracy</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 overflow-y-auto text-xs text-slate-600 leading-relaxed">
          {/* Headline Truth / Accuracy Card */}
          <div className="p-4 bg-blue-50/70 border border-blue-200/80 rounded-xl">
            <div className="font-bold text-slate-900 text-xs mb-1 flex items-center space-x-1.5">
              <Sparkles className="w-4 h-4 text-blue-600" />
              <span>Real Benchmark Results (Claude Opus 5.5)</span>
            </div>
            <p className="text-slate-600 text-xs mb-3">
              Scored against 295 hand-verified book spines across 6 real shelf photographs in Straive's Bookshelf Benchmark.
            </p>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="bg-white p-2.5 rounded-lg border border-blue-200/60 shadow-2xs">
                <div className="text-[10px] text-slate-500 font-medium">Precision</div>
                <div className="text-base font-extrabold text-blue-900 tabular-nums">97%</div>
                <div className="text-[9px] text-slate-400">Rarely hallucinates</div>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-blue-200/60 shadow-2xs">
                <div className="text-[10px] text-slate-500 font-medium">Recall</div>
                <div className="text-base font-extrabold text-blue-900 tabular-nums">82%</div>
                <div className="text-[9px] text-slate-400">Books detected</div>
              </div>
              <div className="bg-white p-2.5 rounded-lg border border-blue-200/60 shadow-2xs">
                <div className="text-[10px] text-slate-500 font-medium">Overall F1</div>
                <div className="text-base font-extrabold text-blue-900 tabular-nums">0.89</div>
                <div className="text-[9px] text-slate-400">Run 2 benchmark</div>
              </div>
            </div>
          </div>

          {/* Three Key Architectural Pillars */}
          <div className="space-y-3">
            <div className="flex items-start space-x-3">
              <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 text-xs font-bold mt-0.5">
                ✓
              </div>
              <div>
                <strong className="text-slate-900 block mb-0.5">AI reads the shelf; deterministic code compares with records</strong>
                <p className="text-slate-600">
                  The vision model is strictly tasked with reading visible titles and authors without guessing. Discrepancy checks (phantom inventory, record errors, misplaced items) are calculated deterministically against the store planogram.
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-3">
              <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 text-xs font-bold mt-0.5">
                ✓
              </div>
              <div>
                <strong className="text-slate-900 block mb-0.5">Zoom-and-verify harness reduces missed items</strong>
                <p className="text-slate-600">
                  On crowded shelves, single-photo scans can miss titles. The production harness tiles the image into high-resolution overlapping sections, re-verifying ambiguous spines to maximize recall.
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-3">
              <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0 text-xs font-bold mt-0.5">
                ✓
              </div>
              <div>
                <strong className="text-slate-900 block mb-0.5">Human in the loop confirms every action</strong>
                <p className="text-slate-600">
                  No automated changes happen without human verification. Store associates confirm physical restocks or relocations with one tap, creating feedback loops that audit AI accuracy.
                </p>
              </div>
            </div>
          </div>

          {/* Simulated vs Real Boundary */}
          <div className="p-3 bg-amber-50/80 border border-amber-200 rounded-lg text-amber-900 text-xs">
            <strong>Data Disclosure:</strong> Shelf photos and AI recognition results come from real model executions. Store inventory counts, velocities, and planograms are simulated for demonstration.
          </div>
        </div>

        {/* Footer with credit */}
        <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <span>Based on Straive's Bookshelf Benchmark (by atharva-729)</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-900 text-white font-medium hover:bg-slate-800 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
