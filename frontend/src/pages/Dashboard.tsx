import React, { useState, useEffect } from 'react';
import { Header } from '../components/Header';
import { ChatInterface } from '../components/ChatInterface';
import { ContractGraphViewer } from '../components/ContractGraphViewer';
import { ImpactView } from '../components/ImpactView';
import { ActivityTimeline } from '../components/ActivityTimeline';
import { PermissionModal } from '../components/PermissionModal';
import { BlueprintModal } from '../components/BlueprintModal';
import { apiService, WebSocketClient } from '../services/api';
import {
  PermissionRequest,
  PermissionDecision,
  ContractGraphData,
  ImpactReport,
  RequirementQuestion,
  ProjectBlueprint,
  AgentActivityLog,
  WSMessage,
} from '../types';

export const Dashboard: React.FC = () => {
  const [ollamaStatus, setOllamaStatus] = useState({
    available: false,
    active_model: 'local-heuristic-engine',
    hardware_recommendation: 'llama3:8b (4-bit)',
  });
  const [language, setLanguage] = useState('en');
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  
  const [messages, setMessages] = useState<Array<{ id: string; role: 'user' | 'assistant'; content: string; timestamp: string }>>([
    {
      id: '1',
      role: 'assistant',
      content: '👋 **Welcome to Sugio Labs!** I am your local, human-controlled AI software development assistant.\n\nI will guide you step-by-step to gather requirements, generate an architectural blueprint, construct a **Contract Graph**, and detect cross-layer impacts before modifying any code.',
      timestamp: new Date().toISOString(),
    },
  ]);
  
  const [currentQuestion, setCurrentQuestion] = useState<RequirementQuestion | null>(null);
  const [graphData, setGraphData] = useState<ContractGraphData>({ nodes: [], edges: [] });
  const [impactReport, setImpactReport] = useState<ImpactReport | null>(null);
  const [pendingPermissions, setPendingPermissions] = useState<PermissionRequest[]>([]);
  const [blueprint, setBlueprint] = useState<ProjectBlueprint | null>(null);
  const [isBlueprintOpen, setIsBlueprintOpen] = useState(false);
  const [logs, setLogs] = useState<AgentActivityLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Initial load
  useEffect(() => {
    loadInitialData();

    // Setup WebSocket
    const ws = new WebSocketClient((msg: WSMessage) => {
      handleWebSocketMessage(msg);
    });
    ws.connect();

    return () => {
      ws.disconnect();
    };
  }, []);

  const loadInitialData = async () => {
    try {
      const [status, q, graph, perms, bp] = await Promise.all([
        apiService.getOllamaStatus(),
        apiService.getCurrentQuestion(),
        apiService.getContractGraph(),
        apiService.getPendingPermissions(),
        apiService.getBlueprint(),
      ]);

      setOllamaStatus(status);
      setCurrentQuestion(q);
      setGraphData(graph);
      setPendingPermissions(perms);
      setBlueprint(bp);
    } catch (e) {
      console.error('Error loading initial dashboard data:', e);
    }
  };

  const handleWebSocketMessage = (msg: WSMessage) => {
    if (msg.type === 'permission_required') {
      setPendingPermissions((prev) => [...prev, msg.payload]);
    } else if (msg.type === 'impact_analysis') {
      setImpactReport(msg.payload);
    } else if (msg.type === 'graph_update') {
      setGraphData(msg.payload);
    } else if (msg.type === 'activity_log') {
      const newLog: AgentActivityLog = {
        id: Math.random().toString(),
        step: msg.payload.step || 'Execution',
        agent_name: msg.payload.agent_name || 'Agent',
        status: 'completed',
        details: msg.payload.details || '',
        timestamp: new Date().toISOString(),
      };
      setLogs((prev) => [newLog, ...prev]);
    } else if (msg.type === 'blueprint_ready') {
      setBlueprint(msg.payload);
      setIsBlueprintOpen(true);
    }
  };

  const handleSendMessage = async (text: string) => {
    const userMsg = {
      id: Math.random().toString(),
      role: 'user' as const,
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await apiService.sendMessage(text, language);
      const assistantMsg = {
        id: Math.random().toString(),
        role: 'assistant' as const,
        content: res.response,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (res.impact_report) {
        setImpactReport(res.impact_report);
      }
      if (res.blueprint) {
        setBlueprint(res.blueprint);
      }
      if (res.activity_logs) {
        setLogs((prev) => [...res.activity_logs, ...prev]);
      }
    } catch (e) {
      console.error('Error sending message:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnswerQuestion = async (qId: string, answer: string) => {
    const userMsg = {
      id: Math.random().toString(),
      role: 'user' as const,
      content: answer,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await apiService.submitAnswer(qId, answer);
      setCurrentQuestion(res.next_question);

      if (res.next_question) {
        const assistantMsg = {
          id: Math.random().toString(),
          role: 'assistant' as const,
          content: `Noted: **${answer}**\n\nNext Question:\n**${res.next_question.question}**\n\n*Recommendation:* ${res.next_question.recommended_option}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } else if (res.is_complete && res.blueprint) {
        setBlueprint(res.blueprint);
        setIsBlueprintOpen(true);
        const assistantMsg = {
          id: Math.random().toString(),
          role: 'assistant' as const,
          content: `🎉 **Requirement interview completed!**\nGenerated project blueprint for **${res.blueprint.project_name}**.\n\nPlease review and approve the blueprint to initialize the Contract Graph.`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
    } catch (e) {
      console.error('Error answering question:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePermissionDecision = async (
    requestId: string,
    decision: PermissionDecision,
    reason?: string
  ) => {
    try {
      await apiService.submitPermissionDecision({ request_id: requestId, decision, reason });
      setPendingPermissions((prev) => prev.filter((p) => p.id !== requestId));
      
      const assistantMsg = {
        id: Math.random().toString(),
        role: 'assistant' as const,
        content: `Permission **${decision.toUpperCase()}** applied for request \`${requestId.slice(0, 8)}\`.`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e) {
      console.error('Error submitting permission decision:', e);
    }
  };

  const handleTriggerDemo = async () => {
    setIsLoading(true);
    try {
      const res = await apiService.triggerStudentDemo();
      setImpactReport(res.impact_report);
      setPendingPermissions((prev) => [...prev, res.permission_request]);

      const demoMsg = {
        id: Math.random().toString(),
        role: 'assistant' as const,
        content: `### 🎯 Student Management System Reference Demo Triggered!\n\n**Requested Change:** \`Add a mandatory phone number to Student.\`\n\nSugio Labs analyzed the Contract Graph across 5 tiers and detected a simulated field mismatch (\`phone\` vs \`phone_number\`).\n\nPermission requested before applying changes!`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, demoMsg]);
    } catch (e) {
      console.error('Error triggering demo:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetDemo = async () => {
    try {
      const res = await apiService.resetDemoGraph();
      setGraphData(res.graph);
    } catch (e) {
      console.error('Error resetting graph:', e);
    }
  };

  const handleApproveBlueprint = async () => {
    try {
      const res = await apiService.approveBlueprint();
      setBlueprint(res.blueprint);
      setIsBlueprintOpen(false);
      const approvalMsg = {
        id: Math.random().toString(),
        role: 'assistant' as const,
        content: `✅ **Blueprint Approved!** Contract Graph initialized with cross-layer nodes (Frontend ↔ API ↔ Backend ↔ Database ↔ Tests). Ready to generate and verify code.`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, approvalMsg]);
    } catch (e) {
      console.error('Error approving blueprint:', e);
    }
  };

  return (
    <div className="app-container">
      {/* Top Header */}
      <Header
        ollamaStatus={ollamaStatus}
        language={language}
        setLanguage={setLanguage}
        voiceEnabled={voiceEnabled}
        setVoiceEnabled={setVoiceEnabled}
        onTriggerDemo={handleTriggerDemo}
        onOpenBlueprint={() => setIsBlueprintOpen(true)}
      />

      {/* Main 3-Column Layout */}
      <main className="main-content">
        {/* Left Column: Chat & Interview Wizard */}
        <section style={{ height: '100%', overflow: 'hidden' }}>
          <ChatInterface
            messages={messages}
            onSendMessage={handleSendMessage}
            currentQuestion={currentQuestion}
            onAnswerQuestion={handleAnswerQuestion}
            isLoading={isLoading}
            voiceEnabled={voiceEnabled}
            language={language}
          />
        </section>

        {/* Center Column: Contract Graph & Impact View */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '14px', height: '100%', overflow: 'hidden' }}>
          {impactReport && (
            <ImpactView impactReport={impactReport} onClear={() => setImpactReport(null)} />
          )}
          <div style={{ flex: 1, minHeight: 0 }}>
            <ContractGraphViewer graphData={graphData} onResetDemo={handleResetDemo} />
          </div>
        </section>

        {/* Right Column: Live Activity Timeline */}
        <aside className="right-sidebar" style={{ height: '100%', overflow: 'hidden' }}>
          <ActivityTimeline logs={logs} />
        </aside>
      </main>

      {/* Permission Gate Modal Dialog */}
      <PermissionModal
        requests={pendingPermissions}
        onDecision={handlePermissionDecision}
      />

      {/* Expandable Blueprint Modal */}
      <BlueprintModal
        blueprint={blueprint}
        isOpen={isBlueprintOpen}
        onClose={() => setIsBlueprintOpen(false)}
        onApprove={handleApproveBlueprint}
      />
    </div>
  );
};
