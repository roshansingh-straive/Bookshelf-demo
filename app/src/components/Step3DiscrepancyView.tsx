import React, { useState } from 'react';
import { ActionTask, ScanMetrics } from '../types';
import {
  ArrowRight,
  CheckCircle2,
  Check,
} from 'lucide-react';

interface Step3DiscrepancyViewProps {
  tasks: ActionTask[];
  metrics: ScanMetrics;
  onResolveTask: (taskId: string) => void;
  hoveredItemId?: string | null;
  onHoverItem?: (id: string | null) => void;
}

export const Step3DiscrepancyView: React.FC<Step3DiscrepancyViewProps> = ({
  tasks,
  metrics,
  onResolveTask,
  hoveredItemId,
  onHoverItem,
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'misplaced' | 'missing' | 'resolved'>('all');

  const openTasks = tasks.filter((t) => !t.resolved);
  const resolvedTasks = tasks.filter((t) => t.resolved);

  const displayedTasks = tasks.filter((t) => {
    if (activeTab === 'resolved') return t.resolved;
    if (t.resolved) return false;
    if (activeTab === 'misplaced') return t.type === 'misplaced_item';
    if (activeTab === 'missing') return t.type === 'missing_item';
    return true;
  });

  const missingCount = openTasks.filter((t) => t.type === 'missing_item').length;
  const misplacedCount = openTasks.filter((t) => t.type === 'misplaced_item').length;

  // Reviewing a task is not a new observation of physical shelf coverage.
  const compliance = metrics.planogram_compliance_pct;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex flex-col h-full">
      {/* Step Header */}
      <div className="p-4 border-b border-slate-100 bg-slate-50/70">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
              3
            </span>
            <h2 className="text-sm font-bold text-slate-900 tracking-tight">Discrepancy &amp; Action Feed</h2>
          </div>
          <span className="text-xs px-2 py-0.5 rounded-full font-bold bg-amber-100 text-amber-800 border border-amber-200">
            {openTasks.length} Checks to Review
          </span>
        </div>
        <p className="text-xs text-slate-500">
          Review possible discrepancies against the photo and physical shelf. Confirmations are saved for this demo session.
        </p>

        {/* Headline Discrepancy KPI Tiles */}
        <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-200/60">
          <div className="bg-white p-2.5 rounded-lg border border-slate-200/80">
            <div className="text-[11px] text-slate-500 font-medium">Titles matched</div>
            <div className="text-lg font-bold text-slate-900 tabular-nums">
              {compliance}%
            </div>
          </div>
          <div className="bg-white p-2.5 rounded-lg border border-slate-200/80">
            <div className="text-[11px] text-slate-500 font-medium">Unconfirmed</div>
            <div className="text-lg font-bold text-red-600 tabular-nums">{missingCount}</div>
          </div>
          <div className="bg-white p-2.5 rounded-lg border border-slate-200/80">
            <div className="text-[11px] text-slate-500 font-medium">Possible moves</div>
            <div className="text-lg font-bold text-amber-600 tabular-nums">{misplacedCount}</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-4 py-2 border-b border-slate-100 bg-white flex space-x-1 overflow-x-auto">
        <button
          onClick={() => setActiveTab('all')}
          className={`px-3 py-1 text-xs rounded-md font-medium whitespace-nowrap transition-colors ${
            activeTab === 'all'
              ? 'bg-slate-900 text-white'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          All Checks ({openTasks.length})
        </button>
        <button
          onClick={() => setActiveTab('misplaced')}
          className={`px-3 py-1 text-xs rounded-md font-medium whitespace-nowrap transition-colors ${
            activeTab === 'misplaced'
              ? 'bg-amber-600 text-white'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          Misplaced ({misplacedCount})
        </button>
        <button
          onClick={() => setActiveTab('missing')}
          className={`px-3 py-1 text-xs rounded-md font-medium whitespace-nowrap transition-colors ${
            activeTab === 'missing'
              ? 'bg-red-600 text-white'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          Unconfirmed ({missingCount})
        </button>
        {resolvedTasks.length > 0 && (
          <button
            onClick={() => setActiveTab('resolved')}
            className={`px-3 py-1 text-xs rounded-md font-medium whitespace-nowrap transition-colors ${
              activeTab === 'resolved'
                ? 'bg-emerald-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Resolved ({resolvedTasks.length})
          </button>
        )}
      </div>

      {/* Action Tasks Feed */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5 max-h-[580px]">
        {displayedTasks.length === 0 ? (
          <div className="p-8 text-center">
            <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-2">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div className="text-xs font-bold text-slate-800">
              {activeTab === 'resolved' ? 'No resolved tasks yet' : 'No open checks in this view'}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              {activeTab === 'resolved'
                ? 'Confirming tasks will log them here.'
                : 'A reviewed task does not establish full shelf accuracy. Rescan after physical changes.'}
            </p>
          </div>
        ) : (
          displayedTasks.map((task) => {
            const isMisplaced = task.type === 'misplaced_item';
            const isRecordError = task.type === 'record_error';
            const isPhantom = task.badge.includes('Phantom');

            let cardBorder = 'border-slate-200 bg-white';
            let badgeBg = 'bg-slate-100 text-slate-800';

            if (isMisplaced) {
              cardBorder = 'border-amber-200/90 bg-amber-50/30';
              badgeBg = 'bg-amber-100 text-amber-900 border border-amber-300/80';
            } else if (isPhantom) {
              cardBorder = 'border-rose-200/90 bg-rose-50/30';
              badgeBg = 'bg-rose-100 text-rose-900 border border-rose-300/80';
            } else if (isRecordError) {
              cardBorder = 'border-purple-200/90 bg-purple-50/30';
              badgeBg = 'bg-purple-100 text-purple-900 border border-purple-300/80';
            }

            if (task.resolved) {
              cardBorder = 'border-emerald-200 bg-emerald-50/40 opacity-80';
            }

            return (
              <div
                key={task.id}
                onMouseEnter={() => onHoverItem?.(task.shelf_item_id ?? null)}
                onMouseLeave={() => onHoverItem?.(null)}
                className={`p-3 rounded-lg border transition-all shadow-2xs ${cardBorder} ${task.shelf_item_id && task.shelf_item_id === hoveredItemId ? 'ring-2 ring-blue-300' : ''}`}
              >
                {/* Badge */}
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${badgeBg}`}>
                    {task.badge}
                  </span>
                  {task.resolved && (
                    <span className="inline-flex items-center space-x-1 text-[11px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-300">
                      <Check className="w-3 h-3" />
                      <span>Resolved</span>
                    </span>
                  )}
                </div>

                {/* Title and Author */}
                <div className="text-xs font-bold text-slate-900">{task.title}</div>
                <div className="text-[11px] text-slate-500 mb-1.5">{task.author || 'Author unspecified'}</div>

                {/* Plain-English Issue Description */}
                <div className="text-[11px] text-slate-700 bg-white/80 p-2 rounded border border-slate-200/70 mb-2">
                  <span className="font-semibold">{task.headline}</span>
                </div>

                {/* One-Tap Action Button */}
                {!task.resolved ? (
                  <button
                    onClick={() => onResolveTask(task.id)}
                    className="w-full flex items-center justify-center space-x-1.5 py-1.5 px-3 rounded-md text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:scale-98 shadow-2xs transition-all"
                  >
                    <span>{task.suggested_action}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                ) : (
                  <div className="text-[11px] font-medium text-emerald-700 flex items-center space-x-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Reviewed in this demo session</span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="p-2.5 bg-slate-50 border-t border-slate-200 text-center">
        <span className="text-[11px] text-slate-500 font-medium">
          Review only · Inventory records are not changed · Rescan to refresh coverage
        </span>
      </div>
    </div>
  );
};
