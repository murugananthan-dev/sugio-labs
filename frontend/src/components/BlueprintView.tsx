import React, { useState } from 'react';
import {
  CheckCircle,
  Database,
  Network,
  Layers,
  Edit3,
  XCircle,
  Loader2,
} from 'lucide-react';
import { ProjectBlueprint } from '../types';

interface BlueprintViewProps {
  blueprint: ProjectBlueprint | null;
  onDecision: (decision: 'APPROVE' | 'REJECT' | 'EDIT', modifications?: string) => void;
  deciding: boolean;
  onViewGraph: () => void;
}

export const BlueprintView: React.FC<BlueprintViewProps> = ({
  blueprint,
  onDecision,
  deciding,
  onViewGraph,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'overview' | 'api' | 'db' | 'modules' | 'steps'>('overview');
  const [editMode, setEditMode] = useState(false);
  const [editInstructions, setEditInstructions] = useState('');

  if (!blueprint) {
    return (
      <div className="glass-panel p-8 text-center max-w-xl mx-auto my-8">
        <Layers className="w-12 h-12 text-slate-500 mx-auto mb-4" />
        <h3 className="text-lg font-bold text-white mb-2">No Active Blueprint</h3>
        <p className="text-slate-400 text-sm">
          Complete the Requirement Gathering Interview to generate an architecture blueprint.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto my-6 space-y-6">
      {/* Blueprint Header Banner */}
      <div className="glass-panel p-6 relative overflow-hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="pill pill-indigo">Architecture Specification</span>
            {blueprint.approved ? (
              <span className="pill pill-emerald flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> Approved & Synchronized
              </span>
            ) : (
              <span className="pill pill-amber">Pending Approval</span>
            )}
          </div>
          <h2 className="text-2xl font-bold text-white">{blueprint.project_name}</h2>
          <p className="text-sm text-slate-300 mt-1 max-w-2xl">{blueprint.objective}</p>
        </div>

        <div>
          {!blueprint.approved ? (
            <div className="flex flex-col gap-3">
              {!editMode ? (
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => onDecision('APPROVE')}
                    disabled={deciding}
                    className="btn-emerald text-sm"
                    id="blueprint-approve-btn"
                  >
                    {deciding ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                    <span>{deciding ? 'Processing…' : 'Approve Blueprint'}</span>
                  </button>
                  <button
                    onClick={() => setEditMode(true)}
                    disabled={deciding}
                    className="btn-secondary text-sm"
                    id="blueprint-edit-btn"
                  >
                    <Edit3 className="w-4 h-4" />
                    <span>Request Changes</span>
                  </button>
                  <button
                    onClick={() => onDecision('REJECT')}
                    disabled={deciding}
                    className="btn-danger text-sm"
                    id="blueprint-reject-btn"
                  >
                    <XCircle className="w-4 h-4" />
                    <span>Reject</span>
                  </button>
                </div>
              ) : (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (editInstructions.trim()) {
                      onDecision('EDIT', editInstructions.trim());
                      setEditMode(false);
                      setEditInstructions('');
                    }
                  }}
                  className="space-y-2"
                >
                  <textarea
                    value={editInstructions}
                    onChange={(e) => setEditInstructions(e.target.value)}
                    placeholder="Describe the changes you want to the blueprint (e.g. 'Add React Native mobile app layer', 'Remove Redis caching', 'Use MySQL instead of PostgreSQL')…"
                    rows={3}
                    className="w-full p-2.5 rounded-xl bg-slate-950 border border-white/10 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 resize-none"
                    autoFocus
                  />
                  <div className="flex gap-2">
                    <button type="submit" disabled={!editInstructions.trim() || deciding} className="btn-primary text-sm">
                      <Edit3 className="w-4 h-4" />
                      <span>Submit Changes</span>
                    </button>
                    <button type="button" onClick={() => setEditMode(false)} className="btn-secondary text-sm">Cancel</button>
                  </div>
                </form>
              )}
            </div>
          ) : (
            <button
              onClick={onViewGraph}
              className="btn-primary text-sm"
            >
              <Network className="w-4 h-4" />
              <span>View Execution Plan</span>
            </button>
          )}
        </div>
      </div>

      {/* Tech Stack Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Object.entries(blueprint.selected_stack).map(([key, value]) => (
          <div key={key} className="glass-panel p-4">
            <span className="text-[11px] font-mono uppercase text-slate-400 tracking-wider">
              {key}
            </span>
            <p className="text-sm font-semibold text-white mt-1 truncate" title={value}>
              {value}
            </p>
          </div>
        ))}
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="flex border-b border-white/10 gap-2">
        {[
          { id: 'overview', label: 'Architecture & Requirements' },
          { id: 'api', label: `API Endpoints (${blueprint.api_endpoints.length})` },
          { id: 'db', label: `Database Schema (${blueprint.db_schema.length} tables)` },
          { id: 'modules', label: 'Modules & Structure' },
          { id: 'steps', label: 'Phased Implementation Steps' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id as any)}
            className={`pb-2.5 px-3 text-xs font-medium transition-all ${
              activeSubTab === tab.id
                ? 'border-b-2 border-indigo-500 text-white font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Contents */}
      <div className="glass-panel p-6">
        {activeSubTab === 'overview' && (
          <div className="space-y-6">
            <div>
              <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-2">
                Architecture Summary
              </h4>
              <p className="text-sm text-slate-300 leading-relaxed bg-slate-900/60 p-4 rounded-xl border border-white/5">
                {blueprint.architecture_summary}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-2">
                  Functional Requirements
                </h4>
                <ul className="space-y-2">
                  {blueprint.functional_requirements.map((req, idx) => (
                    <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                      <span className="text-indigo-400 font-mono font-bold">•</span>
                      <span>{req}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-2">
                  Non-Functional Requirements & Safety
                </h4>
                <ul className="space-y-2">
                  {blueprint.non_functional_requirements.map((req, idx) => (
                    <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                      <span className="text-emerald-400 font-mono font-bold">•</span>
                      <span>{req}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {activeSubTab === 'api' && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-slate-200 mb-3">REST API Contract Endpoints</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-white/10 text-slate-400">
                    <th className="py-2.5 px-3">Method</th>
                    <th className="py-2.5 px-3">Endpoint Path</th>
                    <th className="py-2.5 px-3">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-mono">
                  {blueprint.api_endpoints.map((ep, idx) => (
                    <tr key={idx} className="hover:bg-white/5 transition-colors">
                      <td className="py-2.5 px-3">
                        <span
                          className={`pill text-[10px] font-bold ${
                            ep.method === 'GET'
                              ? 'pill-indigo'
                              : ep.method === 'POST'
                              ? 'pill-emerald'
                              : ep.method === 'DELETE'
                              ? 'pill-rose'
                              : 'pill-amber'
                          }`}
                        >
                          {ep.method}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-cyan-300">{ep.path}</td>
                      <td className="py-2.5 px-3 font-sans text-slate-300">{ep.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeSubTab === 'db' && (
          <div className="space-y-6">
            <h4 className="text-sm font-semibold text-slate-200 mb-3">Relational Database Schemas</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {blueprint.db_schema.map((table, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-900 border border-white/5">
                  <div className="flex items-center gap-2 mb-3">
                    <Database className="w-4 h-4 text-cyan-400" />
                    <span className="font-mono font-bold text-sm text-slate-100">{table.table}</span>
                  </div>
                  <ul className="space-y-1 font-mono text-[11px] text-slate-300">
                    {table.columns.map((col, cIdx) => (
                      <li key={cIdx} className="p-1 rounded hover:bg-white/5 flex flex-col justify-center">
                        <span>{col.name}</span>
                        <span className="text-[10px] text-slate-500">({col.type}) {col.constraints}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeSubTab === 'modules' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-sm font-semibold text-indigo-300 mb-3">Frontend Component Modules</h4>
              <div className="space-y-2">
                {blueprint.frontend_modules.map((m, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-slate-900/80 border border-white/5">
                    <span className="font-mono text-xs text-white font-bold">{m.name}</span>
                    <p className="text-[11px] font-mono text-slate-400">{m.path}</p>
                    <p className="text-xs text-slate-300 mt-1">{m.purpose}</p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-cyan-300 mb-3">Backend Service Modules</h4>
              <div className="space-y-2">
                {blueprint.backend_modules.map((m, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-slate-900/80 border border-white/5">
                    <span className="font-mono text-xs text-white font-bold">{m.name}</span>
                    <p className="text-[11px] font-mono text-slate-400">{m.path}</p>
                    <p className="text-xs text-slate-300 mt-1">{m.purpose}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeSubTab === 'steps' && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-slate-200 mb-3">Ordered Development Lifecycle</h4>
            <div className="space-y-2">
              {blueprint.development_steps.map((step, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-slate-900 border border-white/5 flex items-center gap-3">
                  <span className="w-6 h-6 rounded-full bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 text-xs font-bold flex items-center justify-center font-mono">
                    {idx + 1}
                  </span>
                  <span className="text-xs text-slate-200 font-medium">{step}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
