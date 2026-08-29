import React from 'react';
import { FinalExecutionReport } from '../types';
import { CheckCircle2, XCircle, Clock, FileCode, Search, ShieldCheck } from 'lucide-react';

interface FinalReportViewProps {
  report: FinalExecutionReport;
  onClose: () => void;
}

export const FinalReportView: React.FC<FinalReportViewProps> = ({ report, onClose }) => {
  const isSuccess = report.status === 'COMPLETED';

  const formatTime = (timeStr: string) => {
    return new Date(timeStr).toLocaleString();
  };

  return (
    <div className="bg-slate-900 border border-white/10 rounded-xl overflow-hidden flex flex-col h-full max-h-[80vh]">
      <div className="p-4 border-b border-white/10 bg-slate-950 flex justify-between items-center">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          {isSuccess ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <XCircle className="w-5 h-5 text-rose-400" />}
          Execution Report: {report.project_name}
        </h2>
        <button onClick={onClose} className="text-slate-400 hover:text-white px-3 py-1 rounded border border-white/10 bg-slate-800">
          Close
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        
        {/* Top Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-3 bg-slate-800/50 rounded-lg border border-white/5">
            <p className="text-xs text-slate-400 mb-1 flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> Started</p>
            <p className="text-sm font-mono text-slate-200">{formatTime(report.started_at)}</p>
          </div>
          <div className="p-3 bg-slate-800/50 rounded-lg border border-white/5">
            <p className="text-xs text-slate-400 mb-1 flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> Completed</p>
            <p className="text-sm font-mono text-slate-200">{formatTime(report.completed_at)}</p>
          </div>
          <div className="p-3 bg-slate-800/50 rounded-lg border border-white/5">
            <p className="text-xs text-slate-400 mb-1 flex items-center gap-1"><FileCode className="w-3.5 h-3.5" /> Created</p>
            <p className="text-sm font-mono text-slate-200">{report.created_files?.length || 0} files</p>
          </div>
          <div className="p-3 bg-slate-800/50 rounded-lg border border-white/5">
            <p className="text-xs text-slate-400 mb-1 flex items-center gap-1"><FileCode className="w-3.5 h-3.5" /> Modified</p>
            <p className="text-sm font-mono text-slate-200">{report.modified_files?.length || 0} files</p>
          </div>
        </div>

        {/* Status / Error Box */}
        {!isSuccess && report.failure_details && (
          <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30">
            <h3 className="text-rose-400 font-medium mb-2 text-sm flex items-center gap-2">
              <XCircle className="w-4 h-4" /> Execution Failed
            </h3>
            <p className="text-sm text-rose-200">{report.failure_details}</p>
            {report.recovery_action && (
              <p className="mt-2 text-xs text-rose-300">Suggested Action: {report.recovery_action}</p>
            )}
          </div>
        )}

        {/* Blueprint & Requirements Summary */}
        <div className="grid md:grid-cols-2 gap-4">
          <div className="p-4 bg-slate-800/30 rounded-lg border border-white/5">
            <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Requirement Summary</h3>
            <p className="text-sm text-slate-300">{report.requirement_summary || 'N/A'}</p>
          </div>
          <div className="p-4 bg-slate-800/30 rounded-lg border border-white/5">
            <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Blueprint</h3>
            <p className="text-sm text-slate-300">{report.blueprint_summary || 'N/A'}</p>
          </div>
        </div>

        {/* Affected Files */}
        {(report.created_files?.length > 0 || report.modified_files?.length > 0) && (
          <div>
            <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-3 flex items-center gap-2">
              <FileCode className="w-4 h-4" /> Affected Files
            </h3>
            <div className="bg-slate-950 rounded-lg border border-white/10 p-2 overflow-x-auto">
              <ul className="text-xs font-mono text-slate-300 space-y-1">
                {report.created_files.map((f, i) => (
                  <li key={`c-${i}`} className="text-emerald-400 flex items-center gap-2">
                    <span className="w-16 shrink-0">[NEW]</span> {f}
                  </li>
                ))}
                {report.modified_files.map((f, i) => (
                  <li key={`m-${i}`} className="text-indigo-400 flex items-center gap-2">
                    <span className="w-16 shrink-0">[MODIFIED]</span> {f}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Validation and Consistency */}
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-3 flex items-center gap-2">
              <Search className="w-4 h-4" /> Validation Results
            </h3>
            <div className="p-3 bg-slate-950 rounded-lg border border-white/10 text-xs text-slate-300 font-mono whitespace-pre-wrap">
              {report.validation_results || 'No validation output.'}
            </div>
          </div>
          <div>
            <h3 className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-3 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" /> Consistency Check
            </h3>
            <div className={`p-3 bg-slate-950 rounded-lg border border-white/10 text-xs font-mono whitespace-pre-wrap ${
              report.consistency_result?.toLowerCase().includes('drift') ? 'text-amber-400' : 'text-emerald-400'
            }`}>
              {report.consistency_result || 'N/A'}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
