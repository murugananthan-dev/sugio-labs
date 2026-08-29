import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { InterviewWizard } from './components/InterviewWizard';
import { BlueprintView } from './components/BlueprintView';
import { ExecutionPlanView } from './components/ExecutionPlanView';
import { GraphView } from './components/GraphView';
import { ImpactModal } from './components/ImpactModal';
import { GitSafetyView } from './components/GitSafetyView';
import { ChatAssistant } from './components/ChatAssistant';
import { ActivityTimeline } from './components/ActivityTimeline';
import { PermissionModal } from './components/PermissionModal';
import { WorkspaceSetup } from './components/WorkspaceSetup';
import { FinalReportView } from './components/FinalReportView';
import { SessionHistoryView } from './components/SessionHistoryView';
import {
  HealthStatus,
  HardwareProfile,
  RequirementQuestion,
  ProjectBlueprint,
  ContractGraphData,
  ImpactReport,
  PermissionRequest,
  PermissionResponse,
  ExecutionPlan,
  ExecutionResult,
  ExecutionApprovalStatus,
  ProjectWorkspace,
  FinalExecutionReport,
} from './types';
import {
  fetchHealth,
  fetchHardware,
  startPlanning,
  submitPlanningMessage,
  submitBlueprintDecision,
  submitExecutionDecision,
  fetchContractGraph,
  resetSampleGraph,
  submitImpactAnalysis,
  fetchPendingPermissions,
  submitPermissionDecision,
  fetchSessionState,
} from './services/api';
import { useGlobalState } from './context/GlobalContext';
import { useWebSocket } from './services/useWebSocket';

// ─────────────────────────────────────────────────────────────────────────────
// ERROR BANNER — shown for recoverable API errors, auto-dismisses after 6s
// ─────────────────────────────────────────────────────────────────────────────

const ErrorBanner: React.FC<{ message: string; onDismiss: () => void }> = ({
  message,
  onDismiss,
}) => (
  <div
    role="alert"
    className="fixed top-4 right-4 z-50 max-w-md glass-panel border border-rose-500/30 bg-rose-950/40 p-4 flex items-start gap-3"
  >
    <span className="text-rose-400 text-lg leading-none">⚠</span>
    <div className="flex-1">
      <p className="text-sm font-semibold text-rose-300">Error</p>
      <p className="text-xs text-rose-200 mt-0.5 leading-relaxed">{message}</p>
    </div>
    <button
      onClick={onDismiss}
      className="text-slate-400 hover:text-white text-lg leading-none"
    >
      ×
    </button>
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// APP
// ─────────────────────────────────────────────────────────────────────────────

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('interview');
  const [language, setLanguage] = useState<string>('en');
  const [error, setError] = useState<string | null>(null);

  const {
    health, setHealth,
    hardware, setHardware,
    pendingPermission, setPendingPermission,
    activityLogs, appendActivityLog,
    voiceEnabled, setVoiceEnabled,
    speakAnnouncement,
  } = useGlobalState();

  // ── Interview Wizard State ──────────────────────────────────────────────

  /** The backend's current_question is a raw string from the LLM.
   *  We adapt it into the RequirementQuestion shape the wizard expects. */
  const [currentQuestion, setCurrentQuestion] = useState<RequirementQuestion | null>(null);
  const [questionNumber, setQuestionNumber] = useState<number>(1);
  const totalQuestions = 7; // estimate; wizard shows progress up to this
  const [wizardLoading, setWizardLoading] = useState<boolean>(false);
  const [wizardStarted, setWizardStarted] = useState<boolean>(false);

  // ── Blueprint State ────────────────────────────────────────────────────

  const [blueprint, setBlueprint] = useState<ProjectBlueprint | null>(null);
  const [blueprintDeciding, setBlueprintDeciding] = useState<boolean>(false);

  // ── Execution Plan State ───────────────────────────────────────────────

  const [executionPlan, setExecutionPlan] = useState<ExecutionPlan | null>(null);
  const [executionApprovalStatus, setExecutionApprovalStatus] = useState<ExecutionApprovalStatus>('NONE');
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [executionResults, setExecutionResults] = useState<ExecutionResult[]>([]);
  const [executionLoading, setExecutionLoading] = useState<boolean>(false);
  const [checkpointId, setCheckpointId] = useState<string | null>(null);

  // ── Graph State ────────────────────────────────────────────────────────

  const [graphData, setGraphData] = useState<ContractGraphData | null>(null);
  const [graphLoading, setGraphLoading] = useState<boolean>(false);

  // ── Workspace State ──────────────────────────────────────────────────────
  const [workspace, setWorkspace] = useState<ProjectWorkspace | null>(null);

  const [showHistory, setShowHistory] = useState<boolean>(false);
  const [finalReport, setFinalReport] = useState<FinalExecutionReport | null>(null);

  // ── Impact Analysis State ──────────────────────────────────────────────

  const [impactReport, setImpactReport] = useState<ImpactReport | null>(null);
  const [impactLoading, setImpactLoading] = useState<boolean>(false);

  // ─────────────────────────────────────────────────────────────────────────
  // Error helpers
  // ─────────────────────────────────────────────────────────────────────────

  const showError = useCallback((msg: string) => {
    setError(msg);
    // Auto-dismiss after 6 s
    setTimeout(() => setError((prev) => (prev === msg ? null : prev)), 6000);
  }, []);

  // ─────────────────────────────────────────────────────────────────────────
  // WebSocket – realtime push events
  // ─────────────────────────────────────────────────────────────────────────

  const handleWsMessage = useCallback(
    (data: any) => {
      const { type, payload } = data;

      if (type === 'activity_log' && payload) {
        appendActivityLog(payload);
      } else if (type === 'permission_required' && payload) {
        setPendingPermission(payload);
        speakAnnouncement(`Permission required for ${payload.action}`);
      } else if (type === 'graph_update' && payload) {
        setGraphData(payload);
      } else if (type === 'blueprint_ready' && payload?.blueprint) {
        setBlueprint(payload.blueprint);
        speakAnnouncement('Project blueprint is ready for your review.');
        setActiveTab('blueprint');
      } else if (type === 'requirement_question' && payload) {
        // Backend pushed next question over WS
        setCurrentQuestion({
          id: `q_${questionNumber}`,
          question: typeof payload === 'string' ? payload : payload.question ?? String(payload),
          category: 'general',
          options: [],
        });
      } else if (type === 'execution_completed' && payload?.report) {
        setFinalReport(payload.report);
      } else if (type === 'execution_failed' && payload?.report) {
        if (payload.final_report) setFinalReport(payload.final_report);
        else setFinalReport(payload.report);
      }
    },
    [appendActivityLog, setPendingPermission, speakAnnouncement, questionNumber]
  );

  const { isConnected } = useWebSocket(handleWsMessage);

  // ─────────────────────────────────────────────────────────────────────────
  // Initial data load — health, hardware, graph, pending permissions
  // ─────────────────────────────────────────────────────────────────────────

  useEffect(() => {
    const init = async () => {
      const [h, hw, g, p] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchHardware().catch(() => null),
        fetchContractGraph().catch(() => null),
        fetchPendingPermissions().catch(() => [] as PermissionRequest[]),
      ]);

      if (h) setHealth(h);
      if (hw) setHardware(hw);
      if (g) setGraphData(g);
      if (p && p.length > 0) setPendingPermission(p[0]);

      // Attempt session recovery — if server already has state (e.g. page refresh)
      try {
        const session = await fetchSessionState();
        if (session.has_blueprint && session.blueprint) {
          setBlueprint(session.blueprint);
        }
        if (session.has_execution_plan && session.execution_plan) {
          setExecutionPlan(session.execution_plan);
          setExecutionApprovalStatus(session.execution_approval_status);
          setCurrentStepIndex(session.current_step_index ?? 0);
          setExecutionResults(session.execution_results ?? []);
          setCheckpointId(session.checkpoint_id ?? null);
        }
        if (session.workspace) {
          setWorkspace(session.workspace);
        }
        if (session.final_report) {
          setFinalReport(session.final_report);
        }
      } catch {
        // No active session — that's fine, user will start fresh
      }
    };

    init();
  }, [setHealth, setHardware, setPendingPermission]);

  // ─────────────────────────────────────────────────────────────────────────
  // Helper: convert backend current_question string → RequirementQuestion
  // ─────────────────────────────────────────────────────────────────────────

  function adaptQuestion(rawQuestion: string, qNum: number): RequirementQuestion {
    return {
      id: `q_${qNum}`,
      question: rawQuestion,
      category: 'requirement',
      options: [],
      recommended_option: undefined,
      recommendation_reason: undefined,
    };
  }

  // ─────────────────────────────────────────────────────────────────────────
  // START INTERVIEW — user clicks "Start Requirement Wizard"
  // ─────────────────────────────────────────────────────────────────────────

  const handleStartWizard = async () => {
    setWizardLoading(true);
    setWizardStarted(true);
    setQuestionNumber(1);
    setBlueprint(null);
    setExecutionPlan(null);
    setExecutionApprovalStatus('NONE');
    setExecutionResults([]);
    try {
      const res = await startPlanning('Hello, I want to start a new project.', language);
      if (res.current_question) {
        setCurrentQuestion(adaptQuestion(res.current_question, 1));
      } else if (res.requirements_complete && res.blueprint) {
        // Immediate blueprint (unlikely but handle it)
        setBlueprint(res.blueprint);
        setActiveTab('blueprint');
      }
    } catch (err: any) {
      showError(err.message ?? 'Failed to start the interview. Is the backend running?');
      setWizardStarted(false);
    } finally {
      setWizardLoading(false);
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // SUBMIT ANSWER — user picks an option or writes a custom answer
  // ─────────────────────────────────────────────────────────────────────────

  const handleWizardAnswer = async (questionId: string, answer: string) => {
    setWizardLoading(true);
    try {
      const res = await submitPlanningMessage(answer, language);

      if (res.status === 'blocked') {
        // Waiting for approval — blueprint is ready, navigate there
        if (blueprint) setActiveTab('blueprint');
        return;
      }

      if (res.requirements_complete && res.blueprint) {
        // Blueprint generated
        setBlueprint(res.blueprint);
        setCurrentQuestion(null);
        speakAnnouncement('Project blueprint ready for your review.');
        setActiveTab('blueprint');
      } else if (res.current_question) {
        setCurrentQuestion(adaptQuestion(res.current_question, questionNumber + 1));
        setQuestionNumber((prev) => prev + 1);
      }
    } catch (err: any) {
      showError(err.message ?? 'Failed to submit answer.');
    } finally {
      setWizardLoading(false);
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // BLUEPRINT DECISION — APPROVE / EDIT / REJECT
  // ─────────────────────────────────────────────────────────────────────────

  const handleBlueprintDecision = async (
    decision: 'APPROVE' | 'REJECT' | 'EDIT',
    modifications?: string
  ) => {
    setBlueprintDeciding(true);
    try {
      await submitBlueprintDecision(decision, modifications);

      if (decision === 'APPROVE') {
        // Mark blueprint as approved locally
        if (blueprint) setBlueprint({ ...blueprint, approved: true });
        speakAnnouncement('Blueprint approved. Generating execution plan.');

        // The backend now generates the execution plan synchronously.
        // Fetch updated session state to get it.
        try {
          const session = await fetchSessionState();
          if (session.has_execution_plan && session.execution_plan) {
            setExecutionPlan(session.execution_plan);
            setExecutionApprovalStatus(session.execution_approval_status);
            setCurrentStepIndex(0);
            setExecutionResults([]);
            speakAnnouncement('Execution plan ready. Please review before proceeding.');
            setActiveTab('execution');
          }
          // Also refresh graph if available
          if (session.graph) {
            setGraphData(session.graph);
          }
        } catch {
          // Session fetch failed — navigate to execution tab anyway and let user refresh
          setActiveTab('execution');
        }
      } else if (decision === 'REJECT') {
        speakAnnouncement('Blueprint rejected.');
        setBlueprint(null);
        setActiveTab('interview');
      } else if (decision === 'EDIT') {
        speakAnnouncement('Edit request submitted. Regenerating requirements.');
        setBlueprint(null);
        setActiveTab('interview');
        // Re-submit modifications as a planning message so the backend re-interviews
        if (modifications) {
          setWizardLoading(true);
          try {
            const res = await submitPlanningMessage(modifications, language);
            if (res.current_question) {
              setCurrentQuestion(adaptQuestion(res.current_question, 1));
              setQuestionNumber(1);
            } else if (res.requirements_complete && res.blueprint) {
              setBlueprint(res.blueprint);
              setActiveTab('blueprint');
            }
          } catch (err: any) {
            showError(err.message ?? 'Failed to submit edit request.');
          } finally {
            setWizardLoading(false);
          }
        }
      }
    } catch (err: any) {
      showError(err.message ?? 'Blueprint decision failed.');
    } finally {
      setBlueprintDeciding(false);
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // EXECUTION DECISION — APPROVE / EDIT / REJECT
  // ─────────────────────────────────────────────────────────────────────────

  const handleExecutionDecision = async (
    decision: 'APPROVE' | 'REJECT' | 'EDIT' | 'FIX' | 'RETRY' | 'ROLLBACK',
    modifications?: string
  ) => {
    setExecutionLoading(true);
    try {
      const res = await submitExecutionDecision(decision, modifications);
      setExecutionApprovalStatus(res.execution_approval_status);

      if (decision === 'APPROVE') speakAnnouncement('Execution approved. Agent is now coding.');
      if (decision === 'REJECT') speakAnnouncement('Execution cancelled. No files were modified.');
      if (decision === 'EDIT') speakAnnouncement('Revision requested. Regenerating execution plan.');
      if (decision === 'FIX') speakAnnouncement('Fix requested. Regenerating failed step.');
      if (decision === 'RETRY') speakAnnouncement('Retrying failed step.');
      if (decision === 'ROLLBACK') speakAnnouncement('Rollback initiated.');

      // Fetch updated results after decision completes
      try {
        const session = await fetchSessionState();
        setCurrentStepIndex(session.current_step_index ?? 0);
        setExecutionResults(session.execution_results ?? []);
        setCheckpointId(session.checkpoint_id ?? null);
        setExecutionApprovalStatus(session.execution_approval_status);
        if (session.execution_plan) setExecutionPlan(session.execution_plan);
      } catch {
        // Non-fatal — results will be stale but status is updated
      }
    } catch (err: any) {
      showError(err.message ?? `Execution decision '${decision}' failed.`);
    } finally {
      setExecutionLoading(false);
    }
  };



  // ─────────────────────────────────────────────────────────────────────────
  // CONTRACT GRAPH
  // ─────────────────────────────────────────────────────────────────────────

  const handleRefreshGraph = async () => {
    setGraphLoading(true);
    try {
      const g = await fetchContractGraph();
      setGraphData(g);
    } catch (err: any) {
      showError(err.message ?? 'Failed to refresh contract graph.');
    } finally {
      setGraphLoading(false);
    }
  };

  const handleResetSampleGraph = async () => {
    setGraphLoading(true);
    try {
      const res = await resetSampleGraph();
      setGraphData(res.graph);
      speakAnnouncement('Reference Student Management System Contract Graph loaded.');
    } catch (err: any) {
      showError(err.message ?? 'Failed to reset sample graph.');
    } finally {
      setGraphLoading(false);
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // IMPACT ANALYSIS
  // ─────────────────────────────────────────────────────────────────────────

  const handleRunImpactAnalysis = async (entity: string, desc: string) => {
    setImpactLoading(true);
    try {
      const res = await submitImpactAnalysis(entity, desc);
      setImpactReport(res.impact_report);
      if (res.permission_request) setPendingPermission(res.permission_request);
      speakAnnouncement(`Impact analysis complete. Risk level: ${res.impact_report.risk_level}`);
    } catch (err: any) {
      showError(err.message ?? 'Impact analysis failed.');
    } finally {
      setImpactLoading(false);
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // PERMISSION DECISION
  // ─────────────────────────────────────────────────────────────────────────

  const handlePermissionDecision = async (decision: PermissionResponse) => {
    try {
      await submitPermissionDecision(decision);
      setPendingPermission(null);
      speakAnnouncement(
        `Permission ${decision.decision === 'reject' ? 'rejected' : 'granted'}`
      );
    } catch (err: any) {
      showError(err.message ?? 'Failed to submit permission decision.');
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // COMPUTED
  // ─────────────────────────────────────────────────────────────────────────

  const executionPlanReady =
    executionPlan !== null &&
    executionApprovalStatus === 'WAITING_FOR_EXECUTION_APPROVAL';

  // ─────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-indigo-500 selection:text-white">

      {/* Floating error banner */}
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {/* Workspace Setup Modal */}
      {!workspace && (
        <WorkspaceSetup
          onWorkspaceReady={(ws) => {
            setWorkspace(ws);
            speakAnnouncement(`Workspace ${ws.project_name} ready.`);
          }}
          onError={showError}
        />
      )}

      {/* Top Header & Navigation */}
      <Header
        health={health}
        hardware={hardware}
        language={language}
        setLanguage={setLanguage}
        voiceEnabled={voiceEnabled}
        setVoiceEnabled={setVoiceEnabled}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        executionPlanReady={executionPlanReady}
      />
      <div className="flex justify-end px-6 pt-4 max-w-7xl mx-auto w-full">
        <button onClick={() => setShowHistory(true)} className="text-xs px-3 py-1.5 rounded-lg border border-white/10 bg-slate-800 text-white hover:bg-slate-700 transition-colors">
          View History
        </button>
      </div>

      {showHistory ? (
        <div className="flex-1 w-full max-w-7xl mx-auto px-6 py-8">
          <SessionHistoryView onClose={() => setShowHistory(false)} />
        </div>
      ) : finalReport ? (
        <div className="flex-1 w-full max-w-7xl mx-auto px-6 py-8">
          <FinalReportView
            report={finalReport}
            onClose={() => setFinalReport(null)}
          />
        </div>
      ) : (
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-4 gap-6">

        {/* Main Content Area (3 cols on desktop) */}
        <div className="lg:col-span-3">

          {activeTab === 'interview' && (
            <InterviewWizard
              question={wizardStarted ? currentQuestion : null}
              questionNumber={questionNumber}
              totalQuestions={totalQuestions}
              loading={wizardLoading}
              onAnswer={handleWizardAnswer}
              onRestart={handleStartWizard}
              language={language}
            />
          )}

          {activeTab === 'blueprint' && (
            <BlueprintView
              blueprint={blueprint}
              onDecision={handleBlueprintDecision}
              deciding={blueprintDeciding}
              onViewGraph={() => setActiveTab('execution')}
            />
          )}

          {activeTab === 'execution' && executionPlan && (
            <ExecutionPlanView
              plan={executionPlan}
              approvalStatus={executionApprovalStatus}
              currentStepIndex={currentStepIndex}
              executionResults={executionResults}
              loading={executionLoading}
              checkpointId={checkpointId}
              onDecision={handleExecutionDecision}
            />
          )}

          {activeTab === 'execution' && !executionPlan && (
            <div className="glass-panel p-8 text-center max-w-xl mx-auto my-8">
              <span className="text-4xl mb-4 block">🚀</span>
              <h3 className="text-lg font-bold text-white mb-2">No Execution Plan Yet</h3>
              <p className="text-slate-400 text-sm">
                Approve your Architecture Blueprint to generate an execution plan.
                The agent will break down your project into safe, ordered steps.
              </p>
              {blueprint && !blueprint.approved && (
                <button
                  onClick={() => setActiveTab('blueprint')}
                  className="btn-primary mt-4"
                >
                  Go to Blueprint
                </button>
              )}
            </div>
          )}

          {activeTab === 'graph' && (
            <GraphView
              graph={graphData}
              onRefresh={handleRefreshGraph}
              onResetSample={handleResetSampleGraph}
              loading={graphLoading}
            />
          )}

          {activeTab === 'impact' && (
            <ImpactModal
              onAnalyze={handleRunImpactAnalysis}
              loading={impactLoading}
              impactReport={impactReport}
            />
          )}

          {activeTab === 'checkpoints' && (
            <GitSafetyView onSpeak={speakAnnouncement} />
          )}

          {activeTab === 'chat' && (
            <ChatAssistant
              language={language}
              setLanguage={setLanguage}
              voiceEnabled={voiceEnabled}
            />
          )}
        </div>

        {/* Sidebar (1 col on desktop) */}
        <div className="space-y-4">
          <ActivityTimeline logs={activityLogs} />

          {/* System Quick-Info Card */}
          <div className="glass-panel p-4 text-xs space-y-3">
            <h4 className="font-bold text-white uppercase tracking-wider font-mono">
              Core Differentiator
            </h4>
            <p className="text-slate-300 leading-relaxed">
              <strong>Contract Graph:</strong> Prevents schema drifts between Frontend,
              Backend, API, DB, and Tests through continuous semantic verification.
            </p>

            {/* Execution status summary when active */}
            {executionPlan && (
              <div className="pt-2 border-t border-white/5 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Execution Plan</span>
                  <span className={`font-mono font-bold ${
                    executionApprovalStatus === 'APPROVED' ? 'text-emerald-400' :
                    executionApprovalStatus === 'REJECTED' ? 'text-rose-400' :
                    executionApprovalStatus === 'WAITING_FOR_EXECUTION_APPROVAL' ? 'text-amber-400' :
                    'text-slate-400'
                  }`}>
                    {executionApprovalStatus.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Steps</span>
                  <span className="font-mono text-white">
                    {executionResults.length}/{executionPlan.ordered_steps.length}
                  </span>
                </div>
                {checkpointId && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Checkpoint</span>
                    <span className="font-mono text-emerald-400 text-[10px] truncate max-w-[100px]">
                      {checkpointId.slice(0, 12)}…
                    </span>
                  </div>
                )}
              </div>
            )}

            <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-400">
              <span>Workspace</span>
              <span className="text-emerald-400 font-bold max-w-[120px] truncate" title={workspace?.root_path}>
                {workspace ? workspace.project_name : 'None'}
              </span>
            </div>

            <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-400">
              <span>Local-First Execution</span>
              <span className="text-emerald-400 font-bold">100% Private</span>
            </div>

            {/* WebSocket status */}
            <div className="flex items-center gap-1.5 text-[11px]">
              <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
              <span className="text-slate-400">
                {isConnected ? 'Live backend connection' : 'Backend offline — polling disabled'}
              </span>
            </div>
          </div>
        </div>
      </main>
      )}

      {/* Permission Approval Modal Overlay */}
      {pendingPermission && (
        <PermissionModal
          request={pendingPermission}
          onDecision={handlePermissionDecision}
        />
      )}
    </div>
  );
};
