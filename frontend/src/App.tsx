import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { InterviewWizard } from './components/InterviewWizard';
import { BlueprintView } from './components/BlueprintView';
import { GraphView } from './components/GraphView';
import { ImpactModal } from './components/ImpactModal';
import { GitSafetyView } from './components/GitSafetyView';
import { ChatAssistant } from './components/ChatAssistant';
import { ActivityTimeline } from './components/ActivityTimeline';
import { PermissionModal } from './components/PermissionModal';
import {
  HealthStatus,
  HardwareProfile,
  RequirementQuestion,
  ProjectBlueprint,
  ContractGraphData,
  ImpactReport,
  PermissionRequest,
  PermissionResponse,
  AgentActivityLog,
} from './types';
import {
  fetchHealth,
  fetchHardware,
  startInterview,
  submitAnswer,
  approveBlueprint,
  fetchContractGraph,
  resetSampleGraph,
  submitImpactAnalysis,
  fetchPendingPermissions,
  submitPermissionDecision,
  createWebSocketConnection,
} from './services/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('interview');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [hardware, setHardware] = useState<HardwareProfile | null>(null);
  const [language, setLanguage] = useState<string>('en');
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(true);

  // Wizard State
  const [currentQuestion, setCurrentQuestion] = useState<RequirementQuestion | null>(null);
  const [questionNumber, setQuestionNumber] = useState<number>(1);
  const totalQuestions = 7;
  const [wizardLoading, setWizardLoading] = useState<boolean>(false);

  // Blueprint & Graph State
  const [blueprint, setBlueprint] = useState<ProjectBlueprint | null>(null);
  const [approvingBlueprint, setApprovingBlueprint] = useState<boolean>(false);
  const [graphData, setGraphData] = useState<ContractGraphData | null>(null);
  const [graphLoading, setGraphLoading] = useState<boolean>(false);

  // Impact Analysis State
  const [impactReport, setImpactReport] = useState<ImpactReport | null>(null);
  const [impactLoading, setImpactLoading] = useState<boolean>(false);

  // Permission & Activity State
  const [pendingPermission, setPendingPermission] = useState<PermissionRequest | null>(null);
  const [activityLogs, setActivityLogs] = useState<AgentActivityLog[]>([]);

  // Speech synthesizer
  const speakAnnouncement = useCallback(
    (text: string) => {
      if (!voiceEnabled || !('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      window.speechSynthesis.speak(utterance);
    },
    [voiceEnabled]
  );

  // Initial Load
  useEffect(() => {
    const initData = async () => {
      try {
        const [h, hw, g, p] = await Promise.all([
          fetchHealth().catch(() => null),
          fetchHardware().catch(() => null),
          fetchContractGraph().catch(() => null),
          fetchPendingPermissions().catch(() => []),
        ]);

        if (h) setHealth(h);
        if (hw) setHardware(hw);
        if (g) setGraphData(g);
        if (p && p.length > 0) setPendingPermission(p[0]);

        // Start wizard
        const startRes = await startInterview().catch(() => null);
        if (startRes?.question) {
          setCurrentQuestion(startRes.question);
        }
      } catch (err) {
        console.error('Initialization error:', err);
      }
    };

    initData();

    // Setup WebSocket
    const ws = createWebSocketConnection((data) => {
      if (data.type === 'activity_log' && data.payload) {
        setActivityLogs((prev) => [...prev, data.payload]);
      } else if (data.type === 'permission_required' && data.payload) {
        setPendingPermission(data.payload);
        speakAnnouncement(`Permission required for ${data.payload.action}`);
      } else if (data.type === 'graph_update' && data.payload) {
        setGraphData(data.payload);
      }
    });

    return () => {
      ws.close();
    };
  }, [speakAnnouncement]);

  // Handle Wizard Answer
  const handleWizardAnswer = async (questionId: string, answer: string) => {
    setWizardLoading(true);
    try {
      const res = await submitAnswer(questionId, answer);
      if (res.status === 'next_question' && res.question) {
        setCurrentQuestion(res.question);
        setQuestionNumber((prev) => prev + 1);
      } else if (res.status === 'blueprint_ready' && res.blueprint) {
        setBlueprint(res.blueprint);
        setActiveTab('blueprint');
        speakAnnouncement('Project blueprint ready for your review.');
      }
    } catch (err) {
      console.error('Error submitting answer:', err);
    } finally {
      setWizardLoading(false);
    }
  };

  // Restart Wizard
  const handleRestartWizard = async () => {
    setWizardLoading(true);
    try {
      const res = await startInterview();
      setCurrentQuestion(res.question);
      setQuestionNumber(1);
      setBlueprint(null);
    } catch (err) {
      console.error('Error restarting wizard:', err);
    } finally {
      setWizardLoading(false);
    }
  };

  // Approve Blueprint
  const handleApproveBlueprint = async () => {
    setApprovingBlueprint(true);
    try {
      const res = await approveBlueprint();
      setBlueprint(res.blueprint);
      setGraphData(res.graph);
      speakAnnouncement('Blueprint approved. Contract Graph initialized.');
      setActiveTab('graph');
    } catch (err) {
      console.error('Error approving blueprint:', err);
    } finally {
      setApprovingBlueprint(false);
    }
  };

  // Graph Refresh & Reset
  const handleRefreshGraph = async () => {
    setGraphLoading(true);
    try {
      const g = await fetchContractGraph();
      setGraphData(g);
    } catch (err) {
      console.error('Error refreshing graph:', err);
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
    } catch (err) {
      console.error('Error resetting graph:', err);
    } finally {
      setGraphLoading(false);
    }
  };

  // Impact Analysis
  const handleRunImpactAnalysis = async (entity: string, desc: string) => {
    setImpactLoading(true);
    try {
      const res = await submitImpactAnalysis(entity, desc);
      setImpactReport(res.impact_report);
      if (res.permission_request) {
        setPendingPermission(res.permission_request);
      }
      speakAnnouncement(`Impact analysis complete. Risk level: ${res.impact_report.risk_level}`);
    } catch (err) {
      console.error('Error running impact analysis:', err);
    } finally {
      setImpactLoading(false);
    }
  };

  // Permission Decision
  const handlePermissionDecision = async (decision: PermissionResponse) => {
    try {
      await submitPermissionDecision(decision);
      setPendingPermission(null);
      speakAnnouncement(`Permission ${decision.decision === 'reject' ? 'rejected' : 'granted'}`);
    } catch (err) {
      console.error('Error submitting permission decision:', err);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-indigo-500 selection:text-white">
      {/* Top Header & Status */}
      <Header
        health={health}
        hardware={hardware}
        language={language}
        setLanguage={setLanguage}
        voiceEnabled={voiceEnabled}
        setVoiceEnabled={setVoiceEnabled}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* Main Workspace Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Content Area (3 Cols on Desktop) */}
        <div className="lg:col-span-3">
          {activeTab === 'interview' && (
            <InterviewWizard
              question={currentQuestion}
              questionNumber={questionNumber}
              totalQuestions={totalQuestions}
              loading={wizardLoading}
              onAnswer={handleWizardAnswer}
              onRestart={handleRestartWizard}
            />
          )}

          {activeTab === 'blueprint' && (
            <BlueprintView
              blueprint={blueprint}
              onApprove={handleApproveBlueprint}
              approving={approvingBlueprint}
              onViewGraph={() => setActiveTab('graph')}
            />
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

        {/* Live Activity & System Sidebar (1 Col on Desktop) */}
        <div className="space-y-4">
          <ActivityTimeline logs={activityLogs} />

          {/* Quick Info Card */}
          <div className="glass-panel p-4 text-xs space-y-3">
            <h4 className="font-bold text-white uppercase tracking-wider font-mono">
              Core Differentiator
            </h4>
            <p className="text-slate-300 leading-relaxed">
              <strong>Contract Graph:</strong> Prevents schema drifts between Frontend, Backend, API, DB, and Tests through continuous semantic verification.
            </p>
            <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-400">
              <span>Local-First Execution</span>
              <span className="text-emerald-400 font-bold">100% Private</span>
            </div>
          </div>
        </div>
      </main>

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
