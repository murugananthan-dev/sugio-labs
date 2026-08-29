import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  Edit3,
  Loader2,
  ChevronDown,
  ChevronRight,
  FileText,
  FilePen,
  Terminal,
  Link2,
  ShieldAlert,
  GitBranch,
  Zap,
  AlertTriangle,
  Clock,
  CheckCheck,
  Ban,
  RotateCcw,
} from 'lucide-react';
import { ExecutionPlan, ExecutionStep, ExecutionResult, ExecutionApprovalStatus } from '../types';

// ============================================================================
// RISK BADGE
// ============================================================================

function RiskBadge({ level }: { level: string }) {
  const map: Record<string, string> = {
    low: 'pill pill-emerald',
    medium: 'pill pill-amber',
    high: 'pill pill-rose',
    critical: 'pill pill-rose',
  };
  const cls = map[level?.toLowerCase()] ?? 'pill pill-indigo';
  return <span className={`${cls} text-[10px]`}>{level?.toUpperCase() ?? 'UNKNOWN'}</span>;
}

// ============================================================================
// STATUS ICON
// ============================================================================

function StepStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />;
    case 'in_progress':
      return <Loader2 className="w-4 h-4 text-indigo-400 animate-spin flex-shrink-0" />;
    case 'failed':
      return <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />;
    case 'waiting_permission':
      return <ShieldAlert className="w-4 h-4 text-amber-400 animate-pulse flex-shrink-0" />;
    default:
      return <Clock className="w-4 h-4 text-slate-500 flex-shrink-0" />;
  }
}

// ============================================================================
// EXECUTION STEP CARD
// ============================================================================

interface StepCardProps {
  step: ExecutionStep;
  index: number;
  result?: ExecutionResult;
  isCurrentStep: boolean;
}

const StepCard: React.FC<StepCardProps> = ({ step, index, result, isCurrentStep }) => {
  const [expanded, setExpanded] = useState(false);

  const borderColor =
    step.status === 'completed'
      ? 'border-emerald-500/30'
      : step.status === 'failed'
      ? 'border-rose-500/30'
      : step.status === 'in_progress'
      ? 'border-indigo-500/40'
      : isCurrentStep
      ? 'border-indigo-500/20'
      : 'border-white/5';

  const bgColor =
    step.status === 'completed'
      ? 'bg-emerald-950/20'
      : step.status === 'failed'
      ? 'bg-rose-950/20'
      : step.status === 'in_progress'
      ? 'bg-indigo-950/30'
      : 'bg-slate-900/60';

  return (
    <div className={`rounded-xl border ${borderColor} ${bgColor} transition-all`}>
      {/* Step Header — always visible */}
      <button
        onClick={() => setExpanded((p) => !p)}
        className="w-full flex items-center gap-3 p-4 text-left"
        aria-expanded={expanded}
      >
        {/* Step Number */}
        <span className="w-7 h-7 rounded-full bg-slate-800 border border-white/10 text-xs font-bold font-mono text-slate-300 flex items-center justify-center flex-shrink-0">
          {index + 1}
        </span>

        <StepStatusIcon status={step.status} />

        {/* Title + badges */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-slate-100 truncate">{step.title}</span>
            <RiskBadge level={step.risk_level} />
            {step.requires_permission && (
              <span className="pill pill-amber text-[9px]">
                <ShieldAlert className="w-2.5 h-2.5" />
                Permission Required
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{step.description}</p>
        </div>

        {/* Expand chevron */}
        <span className="text-slate-500 flex-shrink-0">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </span>
      </button>

      {/* Expanded Detail */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-white/5 pt-3">
          {/* Description */}
          <p className="text-xs text-slate-300 leading-relaxed">{step.description}</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Files to Read */}
            {step.files_to_read.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider mb-1">
                  <FileText className="w-3 h-3 text-cyan-400" />
                  Files to Read
                </div>
                <ul className="space-y-0.5">
                  {step.files_to_read.map((f, i) => (
                    <li key={i} className="font-mono text-[11px] text-cyan-300 truncate">{f}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Files to Modify */}
            {step.files_to_modify.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider mb-1">
                  <FilePen className="w-3 h-3 text-amber-400" />
                  Files to Modify
                </div>
                <ul className="space-y-0.5">
                  {step.files_to_modify.map((f, i) => (
                    <li key={i} className="font-mono text-[11px] text-amber-300 truncate">{f}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Commands */}
          {step.commands.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider mb-1">
                <Terminal className="w-3 h-3 text-violet-400" />
                Shell Commands
              </div>
              <div className="code-block text-[11px] space-y-1">
                {step.commands.map((cmd, i) => (
                  <div key={i} className="text-violet-300">
                    <span className="text-slate-500 select-none">$ </span>{cmd}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Dependencies */}
          {step.dependencies.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <Link2 className="w-3 h-3 text-slate-500" />
              <span className="text-[10px] text-slate-500">Depends on:</span>
              {step.dependencies.map((dep, i) => (
                <span key={i} className="font-mono text-[10px] text-indigo-300 bg-indigo-950/40 px-1.5 py-0.5 rounded">
                  {dep}
                </span>
              ))}
            </div>
          )}

          {/* Execution Result */}
          {result && (
            <div className={`p-3 rounded-lg text-xs border ${result.success ? 'border-emerald-500/30 bg-emerald-950/30' : 'border-rose-500/30 bg-rose-950/30'}`}>
              <div className="flex items-center gap-1.5 font-semibold mb-1">
                {result.success
                  ? <CheckCheck className="w-3.5 h-3.5 text-emerald-400" />
                  : <XCircle className="w-3.5 h-3.5 text-rose-400" />}
                <span className={result.success ? 'text-emerald-300' : 'text-rose-300'}>
                  {result.success ? 'Step Completed Successfully' : 'Step Failed'}
                </span>
              </div>
              {result.output && <p className="text-slate-300 font-mono text-[10px] mt-1">{result.output}</p>}
              {result.error && <p className="text-rose-300 font-mono text-[10px] mt-1">Error: {result.error}</p>}
            </div>
          )}

          {/* Step result_details from backend */}
          {step.result_details && !result && (
            <div className="p-2.5 rounded-lg bg-slate-900 border border-white/5 text-[11px] font-mono text-slate-300">
              {step.result_details}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ============================================================================
// EXECUTION PLAN VIEW
// ============================================================================

interface ExecutionPlanViewProps {
  plan: ExecutionPlan;
  approvalStatus: ExecutionApprovalStatus;
  currentStepIndex: number;
  executionResults: ExecutionResult[];
  loading: boolean;
  checkpointId: string | null;
  onDecision: (decision: 'APPROVE' | 'REJECT' | 'EDIT' | 'FIX' | 'RETRY' | 'ROLLBACK', modifications?: string) => void;
}

export const ExecutionPlanView: React.FC<ExecutionPlanViewProps> = ({
  plan,
  approvalStatus,
  currentStepIndex,
  executionResults,
  loading,
  checkpointId,
  onDecision,
}) => {
  const [editMode, setEditMode] = useState<false | 'EDIT' | 'FIX'>(false);
  const [editInstructions, setEditInstructions] = useState('');

  const resultsByStepId = Object.fromEntries(
    executionResults.map((r) => [r.step_id, r])
  );

  const isExecuting = approvalStatus === 'APPROVED' && executionResults.length < plan.ordered_steps.length;
  const isDone = approvalStatus === 'APPROVED' && executionResults.length === plan.ordered_steps.length;
  const isRejected = approvalStatus === 'REJECTED';
  const isWaiting = approvalStatus === 'WAITING_FOR_EXECUTION_APPROVAL';
  const isEdit = approvalStatus === 'EDIT';

  const successCount = executionResults.filter((r) => r.success).length;
  const failCount = executionResults.filter((r) => !r.success).length;

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editInstructions.trim()) return;
    onDecision(editMode === 'FIX' ? 'FIX' : 'EDIT', editInstructions.trim());
    setEditMode(false);
    setEditInstructions('');
  };

  return (
    <div className="max-w-4xl mx-auto my-6 space-y-5">

      {/* ─── Plan Header ─── */}
      <div className="glass-panel p-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-900/10 via-transparent to-cyan-900/10 pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="pill pill-indigo text-xs">Execution Plan</span>
              <RiskBadge level={plan.overall_risk} />
              {isWaiting && (
                <span className="pill pill-amber text-[10px]">
                  <AlertTriangle className="w-3 h-3" />
                  Awaiting Approval
                </span>
              )}
              {isExecuting && (
                <span className="pill pill-indigo text-[10px]">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Executing…
                </span>
              )}
              {isDone && !failCount && (
                <span className="pill pill-emerald text-[10px]">
                  <CheckCheck className="w-3 h-3" />
                  Completed
                </span>
              )}
              {isDone && failCount > 0 && (
                <span className="pill pill-rose text-[10px]">
                  <XCircle className="w-3 h-3" />
                  Completed with Errors
                </span>
              )}
              {isRejected && (
                <span className="pill pill-rose text-[10px]">
                  <Ban className="w-3 h-3" />
                  Rejected
                </span>
              )}
            </div>

            <p className="text-xs text-slate-300 leading-relaxed mt-2 max-w-2xl">
              {plan.blueprint_context}
            </p>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 flex-shrink-0">
            <div className="glass-panel p-3 text-center">
              <div className="text-lg font-bold font-mono text-white">{plan.ordered_steps.length}</div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Steps</div>
            </div>
            <div className="glass-panel p-3 text-center">
              <div className="text-lg font-bold font-mono text-amber-300">{plan.estimated_affected_files}</div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Files</div>
            </div>
            <div className="glass-panel p-3 text-center">
              <div className="text-lg font-bold font-mono text-cyan-300">{successCount}/{plan.ordered_steps.length}</div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Done</div>
            </div>
          </div>
        </div>

        {/* Validation Strategy */}
        <div className="mt-4 p-3 rounded-xl bg-slate-900/60 border border-white/5 flex items-start gap-2">
          <Zap className="w-4 h-4 text-cyan-400 mt-0.5 flex-shrink-0" />
          <div>
            <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">Validation Strategy</span>
            <p className="text-xs text-slate-300 mt-0.5 font-mono">{plan.validation_strategy}</p>
          </div>
        </div>

        {/* Git Checkpoint Info */}
        {checkpointId && (
          <div className="mt-3 p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/20 flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <div>
              <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-wider">Git Checkpoint Active</span>
              <p className="text-[11px] font-mono text-emerald-300 mt-0.5">{checkpointId}</p>
            </div>
          </div>
        )}
      </div>

      {/* ─── Progress Bar (when executing) ─── */}
      {(isExecuting || isDone) && (
        <div className="glass-panel p-4">
          <div className="flex justify-between text-xs text-slate-400 mb-2">
            <span>Execution Progress</span>
            <span className="font-mono">
              {executionResults.length}/{plan.ordered_steps.length} steps
              {failCount > 0 && <span className="text-rose-400 ml-2">• {failCount} failed</span>}
            </span>
          </div>
          <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-white/5">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                failCount > 0
                  ? 'bg-gradient-to-r from-emerald-500 to-rose-500'
                  : 'bg-gradient-to-r from-indigo-500 via-indigo-400 to-cyan-400'
              }`}
              style={{ width: `${(executionResults.length / plan.ordered_steps.length) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* ─── Approval Controls (when waiting) ─── */}
      {isWaiting && !editMode && failCount === 0 && (
        <div className="glass-panel p-5 border border-amber-500/20 bg-amber-950/10">
          <p className="text-sm text-amber-200 mb-4 font-medium">
            Review the execution plan above. The agent will take a git checkpoint before modifying any files.
            All steps requiring shell commands or file writes need your permission.
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => onDecision('APPROVE')}
              disabled={loading}
              className="btn-emerald"
              id="execution-approve-btn"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              <span>{loading ? 'Starting Execution…' : 'Approve & Execute'}</span>
            </button>
            <button
              onClick={() => setEditMode('EDIT')}
              disabled={loading}
              className="btn-secondary"
              id="execution-edit-btn"
            >
              <Edit3 className="w-4 h-4" />
              <span>Request Revision</span>
            </button>
            <button
              onClick={() => onDecision('REJECT')}
              disabled={loading}
              className="btn-danger"
              id="execution-reject-btn"
            >
              <XCircle className="w-4 h-4" />
              <span>Cancel Execution</span>
            </button>
          </div>
        </div>
      )}

      {/* ─── Failure Controls (when waiting and failed) ─── */}
      {isWaiting && !editMode && failCount > 0 && (
        <div className="glass-panel p-5 border border-rose-500/30 bg-rose-950/20">
          <p className="text-sm text-rose-200 mb-4 font-medium">
            Execution failed at step {currentStepIndex + 1}. Please choose how to proceed:
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => setEditMode('FIX')}
              disabled={loading}
              className="btn-primary"
            >
              <FilePen className="w-4 h-4" />
              <span>Suggest Fix</span>
            </button>
            <button
              onClick={() => onDecision('RETRY')}
              disabled={loading}
              className="btn-secondary"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Retry Step</span>
            </button>
            <button
              onClick={() => onDecision('ROLLBACK')}
              disabled={loading}
              className="btn-danger"
            >
              <GitBranch className="w-4 h-4" />
              <span>Rollback Checkpoint</span>
            </button>
          </div>
        </div>
      )}

      {/* ─── Edit Mode ─── */}
      {editMode && (
        <form onSubmit={handleEditSubmit} className="glass-panel p-5 border border-indigo-500/20 space-y-3">
          <h4 className="text-sm font-semibold text-white flex items-center gap-2">
            <Edit3 className="w-4 h-4 text-indigo-400" />
            Revision Instructions
          </h4>
          <p className="text-xs text-slate-400">
            Describe what you'd like changed in the execution plan. The agent will regenerate the plan with your feedback.
          </p>
          <textarea
            value={editInstructions}
            onChange={(e) => setEditInstructions(e.target.value)}
            placeholder="e.g. 'Skip the frontend steps for now, only generate the backend API first.'"
            rows={4}
            className="w-full p-3 rounded-xl bg-slate-950 border border-white/10 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 resize-none"
            autoFocus
          />
          <div className="flex gap-3">
            <button type="submit" disabled={!editInstructions.trim() || loading} className="btn-primary">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
              <span>Regenerate Plan</span>
            </button>
            <button type="button" onClick={() => setEditMode(false)} className="btn-secondary">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* ─── Rejected State ─── */}
      {isRejected && (
        <div className="glass-panel p-5 border border-rose-500/20 bg-rose-950/10 text-center">
          <Ban className="w-8 h-8 text-rose-400 mx-auto mb-2" />
          <p className="text-sm text-rose-300 font-medium">Execution Cancelled</p>
          <p className="text-xs text-slate-400 mt-1">
            The execution plan was rejected. No files were modified. You can go back to the Blueprint to re-approve.
          </p>
        </div>
      )}

      {/* ─── Edit regeneration notice ─── */}
      {isEdit && (
        <div className="glass-panel p-4 border border-indigo-500/20 flex items-center gap-3">
          <Loader2 className="w-5 h-5 text-indigo-400 animate-spin flex-shrink-0" />
          <p className="text-sm text-indigo-300">Regenerating execution plan with your feedback…</p>
        </div>
      )}

      {/* ─── Step List ─── */}
      <div className="space-y-2">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-mono px-1 flex items-center gap-2">
          <span>Ordered Execution Steps</span>
          <span className="text-slate-600">({plan.ordered_steps.length} total)</span>
        </h3>

        {plan.ordered_steps.map((step, idx) => (
          <StepCard
            key={step.id}
            step={step}
            index={idx}
            result={resultsByStepId[step.id]}
            isCurrentStep={idx === currentStepIndex}
          />
        ))}
      </div>
    </div>
  );
};
