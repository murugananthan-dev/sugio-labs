import React, { useState } from 'react';
import { ShieldAlert, Check, CheckCheck, X, AlertTriangle, FileCode, Terminal } from 'lucide-react';
import { PermissionRequest, PermissionDecision, PermissionResponse } from '../types';

interface PermissionModalProps {
  request: PermissionRequest | null;
  onDecision: (response: PermissionResponse) => void;
}

export const PermissionModal: React.FC<PermissionModalProps> = ({ request, onDecision }) => {
  const [rejectReason, setRejectReason] = useState<string>('');
  const [showRejectInput, setShowRejectInput] = useState<boolean>(false);

  if (!request) return null;

  const getRiskBadge = (level: string) => {
    switch (level.toLowerCase()) {
      case 'critical':
      case 'high':
        return <span className="pill pill-rose">High Risk</span>;
      case 'medium':
        return <span className="pill pill-amber">Medium Risk</span>;
      default:
        return <span className="pill pill-emerald">Low Risk</span>;
    }
  };

  const handleAction = (decision: PermissionDecision) => {
    if (decision === 'reject' && !showRejectInput) {
      setShowRejectInput(true);
      return;
    }
    onDecision({
      request_id: request.id,
      decision,
      reason: decision === 'reject' ? rejectReason : undefined,
    });
    setShowRejectInput(false);
    setRejectReason('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div className="glass-modal max-w-lg w-full p-6 border border-indigo-500/40 shadow-2xl relative">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
              <ShieldAlert className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Action Permission Required</h3>
              <p className="text-xs text-slate-400">Zero-Trust Local Governance Gate</p>
            </div>
          </div>
          {getRiskBadge(request.risk_level)}
        </div>

        {/* Action Description */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-white/5 space-y-3 mb-5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 font-mono">ACTION TYPE</span>
            <span className="pill pill-indigo text-xs font-mono">{request.action}</span>
          </div>

          <div>
            <span className="text-[11px] font-mono text-slate-400 block mb-1">TARGET RESOURCE</span>
            <p className="text-xs font-mono text-cyan-300 bg-slate-950 p-2 rounded border border-white/5 break-all">
              {request.target}
            </p>
          </div>

          {/* Details / Preview */}
          {request.details && Object.keys(request.details).length > 0 && (
            <div>
              <span className="text-[11px] font-mono text-slate-400 block mb-1">MUTATION DETAILS</span>
              <pre className="code-block text-[11px] max-h-36 overflow-y-auto">
                {JSON.stringify(request.details, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Rejection reason write-in */}
        {showRejectInput && (
          <div className="mb-4">
            <label className="text-xs text-slate-300 block mb-1 font-medium">
              Rejection Reason (Feedback for AI agent):
            </label>
            <input
              type="text"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Do not modify database columns directly..."
              className="w-full p-2.5 rounded-lg bg-slate-900 border border-rose-500/40 text-xs text-white focus:outline-none"
              autoFocus
            />
          </div>
        )}

        {/* Decision Buttons */}
        <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-white/10">
          <button
            onClick={() => handleAction('reject')}
            className="btn-danger text-xs"
          >
            <X className="w-3.5 h-3.5" />
            <span>{showRejectInput ? 'Confirm Reject' : 'Reject'}</span>
          </button>

          <button
            onClick={() => handleAction('allow_once')}
            className="btn-secondary text-xs"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Allow Once</span>
          </button>

          <button
            onClick={() => handleAction('allow_for_project')}
            className="btn-primary text-xs"
          >
            <CheckCheck className="w-3.5 h-3.5" />
            <span>Allow for Project</span>
          </button>
        </div>
      </div>
    </div>
  );
};
