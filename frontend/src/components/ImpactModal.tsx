import React, { useState } from 'react';
import {
  AlertTriangle,
  Zap,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Layers,
  Database,
  FileCode,
  Terminal,
  TestTube,
} from 'lucide-react';
import { ImpactReport } from '../types';

interface ImpactModalProps {
  onAnalyze: (entity: string, description: string) => void;
  loading: boolean;
  impactReport: ImpactReport | null;
}

export const ImpactModal: React.FC<ImpactModalProps> = ({
  onAnalyze,
  loading,
  impactReport,
}) => {
  const [targetEntity, setTargetEntity] = useState<string>('Student');
  const [changeDescription, setChangeDescription] = useState<string>(
    'Add mandatory emergency_contact phone field to student profile'
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetEntity.trim() || !changeDescription.trim()) return;
    onAnalyze(targetEntity, changeDescription);
  };

  const presetChanges = [
    {
      entity: 'phone',
      desc: 'Rename field phone to contact_number across forms and database',
    },
    {
      entity: 'Student',
      desc: 'Add mandatory emergency_contact phone field to student profile',
    },
    {
      entity: 'courses',
      desc: 'Add course instructor_id foreign key constraint and backend validation',
    },
  ];

  return (
    <div className="max-w-5xl mx-auto my-6 space-y-6">
      {/* Input Section */}
      <div className="glass-panel p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Cross-Layer Impact Analyzer</h3>
            <p className="text-xs text-slate-400">
              Simulate or execute changes to calculate schema drifts and contract blast radius before mutating files.
            </p>
          </div>
        </div>

        {/* Quick Presets */}
        <div className="mb-4">
          <span className="text-[11px] font-mono uppercase text-slate-400 block mb-2">
            Try Reference College Scenarios:
          </span>
          <div className="flex flex-wrap gap-2">
            {presetChanges.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setTargetEntity(preset.entity);
                  setChangeDescription(preset.desc);
                }}
                className="text-xs px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 hover:border-indigo-500/50 hover:bg-slate-800 text-slate-300 transition-all text-left"
              >
                {preset.desc}
              </button>
            ))}
          </div>
        </div>

        {/* Change Request Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-mono uppercase text-slate-300 block mb-1">
                Target Entity / Module / Field:
              </label>
              <input
                type="text"
                value={targetEntity}
                onChange={(e) => setTargetEntity(e.target.value)}
                placeholder="e.g. Student, phone, courses"
                className="w-full p-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="md:col-span-2">
              <label className="text-xs font-mono uppercase text-slate-300 block mb-1">
                Natural-Language Change Description:
              </label>
              <input
                type="text"
                value={changeDescription}
                onChange={(e) => setChangeDescription(e.target.value)}
                placeholder="Describe the requested feature change or schema update..."
                className="w-full p-2.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="btn-primary text-xs"
            >
              <Zap className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>{loading ? 'Evaluating Contracts...' : 'Run Impact Analysis'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Impact Results Report */}
      {impactReport && (
        <div className="glass-panel p-6 space-y-6 animate-fadeIn">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-bold text-white">Impact Analysis Assessment</span>
                <span
                  className={`pill text-xs ${
                    impactReport.risk_level === 'High'
                      ? 'pill-rose'
                      : impactReport.risk_level === 'Medium'
                      ? 'pill-amber'
                      : 'pill-emerald'
                  }`}
                >
                  {impactReport.risk_level} Blast Radius Risk
                </span>
              </div>
              <p className="text-xs text-slate-300">{impactReport.summary}</p>
            </div>
          </div>

          {/* Explanations & Blast Radius */}
          <div className="space-y-2">
            <span className="text-xs font-mono uppercase text-slate-400">Analysis Breakdown:</span>
            <div className="space-y-1.5">
              {impactReport.explanations.map((exp, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg bg-slate-900/80 border border-white/5 text-xs text-slate-300 flex items-start gap-2"
                >
                  <span className="text-cyan-400 font-bold font-mono">•</span>
                  <span>{exp}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Affected Layers Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {/* Frontend */}
            <div className="p-4 rounded-xl bg-blue-950/20 border border-blue-500/20">
              <div className="flex items-center gap-2 mb-2 text-blue-400 text-xs font-bold font-mono">
                <FileCode className="w-4 h-4" />
                <span>Frontend Layer ({impactReport.affected_frontend.length})</span>
              </div>
              <ul className="text-xs text-slate-300 space-y-1">
                {impactReport.affected_frontend.map((item, idx) => (
                  <li key={idx} className="font-mono text-[11px] truncate" title={item}>
                    • {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* API */}
            <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-500/20">
              <div className="flex items-center gap-2 mb-2 text-cyan-400 text-xs font-bold font-mono">
                <Terminal className="w-4 h-4" />
                <span>API Layer ({impactReport.affected_apis.length})</span>
              </div>
              <ul className="text-xs text-slate-300 space-y-1">
                {impactReport.affected_apis.map((item, idx) => (
                  <li key={idx} className="font-mono text-[11px] truncate" title={item}>
                    • {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* Backend */}
            <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/20">
              <div className="flex items-center gap-2 mb-2 text-indigo-400 text-xs font-bold font-mono">
                <Layers className="w-4 h-4" />
                <span>Backend Services ({impactReport.affected_backend.length})</span>
              </div>
              <ul className="text-xs text-slate-300 space-y-1">
                {impactReport.affected_backend.map((item, idx) => (
                  <li key={idx} className="font-mono text-[11px] truncate" title={item}>
                    • {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* Database */}
            <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/20">
              <div className="flex items-center gap-2 mb-2 text-emerald-400 text-xs font-bold font-mono">
                <Database className="w-4 h-4" />
                <span>Database Schema ({impactReport.affected_database.length})</span>
              </div>
              <ul className="text-xs text-slate-300 space-y-1">
                {impactReport.affected_database.map((item, idx) => (
                  <li key={idx} className="font-mono text-[11px] truncate" title={item}>
                    • {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* Tests */}
            <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/20">
              <div className="flex items-center gap-2 mb-2 text-amber-400 text-xs font-bold font-mono">
                <TestTube className="w-4 h-4" />
                <span>Automated Tests ({impactReport.affected_tests.length})</span>
              </div>
              <ul className="text-xs text-slate-300 space-y-1">
                {impactReport.affected_tests.map((item, idx) => (
                  <li key={idx} className="font-mono text-[11px] truncate" title={item}>
                    • {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
