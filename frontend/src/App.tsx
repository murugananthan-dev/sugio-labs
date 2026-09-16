import React, { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  ChevronRight,
  Circle,
  Code2,
  Cpu,
  Database,
  FileCode2,
  FlaskConical,
  GitBranch,
  Layers3,
  Lock,
  MessageSquare,
  Network,
  Plus,
  RefreshCw,
  RotateCcw,
  Send,
  Server,
  ShieldCheck,
  Sparkles,
  Terminal,
  User,
  Wifi,
  WifiOff,
  Workflow,
  X,
  Zap,
} from 'lucide-react';
import {
  AgentActivityLog,
  ContractGraphData,
  ContractNode,
  GitCheckpoint,
  HealthStatus,
  HardwareProfile,
  ImpactReport,
  PermissionRequest,
  PermissionResponse,
  ProjectBlueprint,
  RequirementQuestion,
} from './types';
import {
  approveBlueprint,
  createCheckpoint,
  fetchCheckpoints,
  fetchContractGraph,
  fetchGitDiff,
  fetchHardware,
  fetchHealth,
  fetchPendingPermissions,
  fetchSessionState,
  rollbackToCheckpoint,
  sendChatMessage,
  startInterview,
  submitAnswer,
  submitImpactAnalysis,
  submitPermissionDecision,
} from './services/api';
import { useWebSocket } from './services/useWebSocket';

type ViewKey = 'plan' | 'blueprint' | 'contracts' | 'impact' | 'git' | 'assistant';
type ChatMessage = { id: string; role: 'user' | 'assistant'; content: string };

const navItems: Array<{ key: ViewKey; label: string; hint: string; icon: React.ComponentType<{ size?: number }> }> = [
  { key: 'plan', label: 'Plan', hint: 'Requirements', icon: Sparkles },
  { key: 'blueprint', label: 'Blueprint', hint: 'Architecture', icon: Workflow },
  { key: 'contracts', label: 'Contracts', hint: 'Cross-layer graph', icon: Network },
  { key: 'impact', label: 'Impact', hint: 'Change analysis', icon: Zap },
  { key: 'git', label: 'Git Safety', hint: 'Checkpoints', icon: GitBranch },
  { key: 'assistant', label: 'Assistant', hint: 'Local AI', icon: MessageSquare },
];

const layerMeta: Record<string, { icon: React.ComponentType<{ size?: number }>; label: string }> = {
  requirement: { icon: Layers3, label: 'Requirement' },
  frontend: { icon: Code2, label: 'Frontend' },
  api: { icon: Server, label: 'API' },
  backend: { icon: Terminal, label: 'Backend' },
  database: { icon: Database, label: 'Database' },
  test: { icon: FlaskConical, label: 'Tests' },
};

function classNames(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ');
}

function AppBadge({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: 'neutral' | 'good' | 'warn' | 'bad' | 'brand' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function EmptyState({ icon: Icon, title, text }: { icon: React.ComponentType<{ size?: number }>; title: string; text: string }) {
  return (
    <div className="empty-state">
      <div className="empty-icon"><Icon size={22} /></div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function LoadingButton({ loading, children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean }) {
  return (
    <button {...props} disabled={loading || props.disabled}>
      {loading ? <RefreshCw size={16} className="spin" /> : null}
      {children}
    </button>
  );
}

export const App: React.FC = () => {
  const [view, setView] = useState<ViewKey>('plan');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [hardware, setHardware] = useState<HardwareProfile | null>(null);
  const [question, setQuestion] = useState<RequirementQuestion | null>(null);
  const [questionIndex, setQuestionIndex] = useState(1);
  const [blueprint, setBlueprint] = useState<ProjectBlueprint | null>(null);
  const [graph, setGraph] = useState<ContractGraphData>({ nodes: [], edges: [] });
  const [activities, setActivities] = useState<AgentActivityLog[]>([]);
  const [pendingPermission, setPendingPermission] = useState<PermissionRequest | null>(null);
  const [impactReport, setImpactReport] = useState<ImpactReport | null>(null);
  const [checkpoints, setCheckpoints] = useState<GitCheckpoint[]>([]);
  const [gitDiff, setGitDiff] = useState('');
  const [targetEntity, setTargetEntity] = useState('Student');
  const [changeDescription, setChangeDescription] = useState('Add an emergency_contact field to the student profile.');
  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'I am your local Sugio Labs engineering agent. Ask me about architecture, contracts, implementation steps, or the current project state.',
    },
  ]);
  const [language, setLanguage] = useState('en');
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleWsMessage = useCallback((data: any) => {
    if (data?.type === 'activity_log' && data.payload) {
      setActivities((prev) => [...prev.slice(-19), data.payload]);
    }
    if (data?.type === 'permission_required' && data.payload) {
      setPendingPermission(data.payload);
    }
    if (data?.type === 'graph_update' && data.payload) {
      setGraph(data.payload);
    }
  }, []);

  const { isConnected } = useWebSocket(handleWsMessage);

  const initialize = useCallback(async () => {
    setBusy('initialize');
    setError(null);
    try {
      const [nextHealth, nextHardware, nextGraph, pending, session, cps] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchHardware().catch(() => null),
        fetchContractGraph().catch(() => ({ nodes: [], edges: [] })),
        fetchPendingPermissions().catch(() => []),
        fetchSessionState().catch(() => null),
        fetchCheckpoints().catch(() => []),
      ]);

      setHealth(nextHealth);
      setHardware(nextHardware);
      setGraph(nextGraph);
      setCheckpoints(cps);
      setPendingPermission(pending[0] ?? null);

      if (session) {
        setActivities(session.activity_logs ?? []);
        if (session.blueprint) setBlueprint(session.blueprint);
        if (session.question_index) setQuestionIndex(Math.min(session.question_index + 1, 7));
      }

      const interview = await startInterview();
      setQuestion(interview.question);
      setQuestionIndex(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to initialize Sugio Labs.');
    } finally {
      setBusy(null);
    }
  }, []);

  useEffect(() => {
    void initialize();
  }, [initialize]);

  const graphLayers = useMemo(() => {
    const order = ['requirement', 'frontend', 'api', 'backend', 'database', 'test'];
    return order.map((key) => ({
      key,
      nodes: graph.nodes.filter((node) => node.node_type === key),
    }));
  }, [graph]);

  const synchronizedNodes = graph.nodes.filter((node) => node.status === 'synchronized').length;
  const contractHealth = graph.nodes.length ? Math.round((synchronizedNodes / graph.nodes.length) * 100) : 0;

  const handleAnswer = async (answer: string) => {
    if (!question) return;
    setBusy('answer');
    setError(null);
    try {
      const result = await submitAnswer(question.id, answer);
      if (result.status === 'next_question' && result.question) {
        setQuestion(result.question);
        setQuestionIndex((value) => Math.min(value + 1, 7));
      }
      if (result.status === 'blueprint_ready' && result.blueprint) {
        setBlueprint(result.blueprint);
        setQuestion(null);
        setView('blueprint');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save answer.');
    } finally {
      setBusy(null);
    }
  };

  const restartInterview = async () => {
    setBusy('restart');
    setError(null);
    try {
      const result = await startInterview();
      setQuestion(result.question);
      setQuestionIndex(1);
      setBlueprint(null);
      setView('plan');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to restart planning.');
    } finally {
      setBusy(null);
    }
  };

  const handleApproveBlueprint = async () => {
    setBusy('approve');
    setError(null);
    try {
      const result = await approveBlueprint();
      setBlueprint(result.blueprint);
      setGraph(result.graph);
      setView('contracts');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to approve blueprint.');
    } finally {
      setBusy(null);
    }
  };

  const runImpact = async (event: FormEvent) => {
    event.preventDefault();
    if (!targetEntity.trim() || !changeDescription.trim()) return;
    setBusy('impact');
    setError(null);
    try {
      const result = await submitImpactAnalysis(targetEntity.trim(), changeDescription.trim());
      setImpactReport(result.impact_report);
      setPendingPermission(result.permission_request ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impact analysis failed.');
    } finally {
      setBusy(null);
    }
  };

  const refreshGit = async () => {
    const [cps, diff] = await Promise.all([fetchCheckpoints(), fetchGitDiff()]);
    setCheckpoints(cps);
    setGitDiff(diff.diff);
  };

  const makeCheckpoint = async () => {
    setBusy('checkpoint');
    setError(null);
    try {
      await createCheckpoint(`Safety checkpoint ${checkpoints.length + 1}`, 'Created from Sugio Labs workspace');
      await refreshGit();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create checkpoint.');
    } finally {
      setBusy(null);
    }
  };

  const rollback = async (checkpointId: string) => {
    setBusy(`rollback:${checkpointId}`);
    setError(null);
    try {
      await rollbackToCheckpoint(checkpointId);
      await refreshGit();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rollback requires an approved Git permission.');
    } finally {
      setBusy(null);
    }
  };

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault();
    const text = chatInput.trim();
    if (!text || busy === 'chat') return;
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: text };
    setMessages((prev) => [...prev, userMessage]);
    setChatInput('');
    setBusy('chat');
    setError(null);
    try {
      const result = await sendChatMessage(text, language);
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'assistant', content: result.reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'The local assistant could not answer that request. Check the backend/Ollama status and try again.',
        },
      ]);
      setError(err instanceof Error ? err.message : 'Assistant request failed.');
    } finally {
      setBusy(null);
    }
  };

  const decidePermission = async (decision: PermissionResponse['decision']) => {
    if (!pendingPermission) return;
    setBusy('permission');
    try {
      await submitPermissionDecision({ request_id: pendingPermission.id, decision });
      setPendingPermission(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to submit permission decision.');
    } finally {
      setBusy(null);
    }
  };

  const renderPlan = () => (
    <div className="view-stack">
      <section className="hero-card">
        <div>
          <AppBadge tone="brand"><Sparkles size={13} /> Project planning</AppBadge>
          <h1>Shape the app before the agent changes code.</h1>
          <p>Sugio turns your decisions into an architecture blueprint, then tracks every contract from interface to database and tests.</p>
        </div>
        <div className="hero-score">
          <span>{Math.round(((questionIndex - 1) / 7) * 100)}%</span>
          <small>plan captured</small>
        </div>
      </section>

      <section className="content-card plan-card">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Question {Math.min(questionIndex, 7)} of 7</span>
            <h2>{question?.question ?? 'Planning complete'}</h2>
          </div>
          <button className="icon-button" onClick={restartInterview} title="Restart planning"><RotateCcw size={17} /></button>
        </div>

        {question ? (
          <div className="choice-grid">
            {question.options.map((option) => {
              const recommended = option === question.recommended_option;
              return (
                <button
                  key={option}
                  className={classNames('choice-card', recommended && 'choice-recommended')}
                  onClick={() => handleAnswer(option)}
                  disabled={busy === 'answer'}
                >
                  <span className="choice-marker">{recommended ? <Sparkles size={16} /> : <Circle size={15} />}</span>
                  <span className="choice-copy">
                    <strong>{option}</strong>
                    {recommended ? <small>{question.recommendation_reason}</small> : <small>Select this configuration</small>}
                  </span>
                  <ChevronRight size={17} />
                </button>
              );
            })}
          </div>
        ) : (
          <EmptyState icon={CheckCircle2} title="Plan complete" text="Your project blueprint is ready for review." />
        )}
      </section>

      <div className="metric-grid three">
        <div className="metric-card"><ShieldCheck size={19} /><div><strong>Permission gated</strong><span>Every critical mutation asks first</span></div></div>
        <div className="metric-card"><Network size={19} /><div><strong>Contract aware</strong><span>Frontend to test dependencies mapped</span></div></div>
        <div className="metric-card"><Lock size={19} /><div><strong>Local first</strong><span>Designed for Ollama and local workspace</span></div></div>
      </div>
    </div>
  );

  const renderBlueprint = () => {
    if (!blueprint) return <EmptyState icon={Workflow} title="No blueprint yet" text="Finish the planning interview to generate your application architecture." />;
    return (
      <div className="view-stack">
        <section className="page-title-row">
          <div>
            <span className="eyebrow">Architecture blueprint</span>
            <h1>{blueprint.project_name}</h1>
            <p>{blueprint.objective}</p>
          </div>
          {blueprint.approved ? <AppBadge tone="good"><CheckCircle2 size={13} /> Approved</AppBadge> : (
            <LoadingButton className="primary-button" loading={busy === 'approve'} onClick={handleApproveBlueprint}>
              Approve architecture <ArrowRight size={16} />
            </LoadingButton>
          )}
        </section>

        <div className="metric-grid four">
          <div className="stat-card"><span>Features</span><strong>{blueprint.features.length}</strong></div>
          <div className="stat-card"><span>API routes</span><strong>{blueprint.api_endpoints.length}</strong></div>
          <div className="stat-card"><span>Frontend modules</span><strong>{blueprint.frontend_modules.length}</strong></div>
          <div className="stat-card"><span>Backend modules</span><strong>{blueprint.backend_modules.length}</strong></div>
        </div>

        <div className="two-column">
          <section className="content-card">
            <div className="section-heading"><div><span className="eyebrow">Selected stack</span><h2>Technology decisions</h2></div></div>
            <div className="stack-list">
              {Object.entries(blueprint.selected_stack).map(([key, value]) => (
                <div className="stack-row" key={key}><span>{key.replace('_', ' ')}</span><strong>{value}</strong></div>
              ))}
            </div>
          </section>
          <section className="content-card">
            <div className="section-heading"><div><span className="eyebrow">Capabilities</span><h2>Core feature set</h2></div></div>
            <div className="check-list">
              {blueprint.features.map((feature) => <div key={feature}><Check size={15} /><span>{feature}</span></div>)}
            </div>
          </section>
        </div>

        <section className="content-card">
          <div className="section-heading"><div><span className="eyebrow">REST surface</span><h2>API contract</h2></div></div>
          <div className="table-shell">
            <table>
              <thead><tr><th>Method</th><th>Path</th><th>Purpose</th></tr></thead>
              <tbody>
                {blueprint.api_endpoints.map((endpoint) => (
                  <tr key={`${endpoint.method}-${endpoint.path}`}>
                    <td><AppBadge tone={endpoint.method === 'GET' ? 'good' : endpoint.method === 'DELETE' ? 'bad' : 'brand'}>{endpoint.method}</AppBadge></td>
                    <td><code>{endpoint.path}</code></td>
                    <td>{endpoint.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    );
  };

  const renderContracts = () => (
    <div className="view-stack">
      <section className="page-title-row">
        <div>
          <span className="eyebrow">Contract graph</span>
          <h1>See the full change path.</h1>
          <p>Each node represents a contract the agent must keep synchronized when your app evolves.</p>
        </div>
        <div className="contract-score"><strong>{contractHealth}%</strong><span>sync health</span></div>
      </section>

      <section className="content-card contract-board">
        <div className="contract-flow">
          {graphLayers.map((layer, index) => {
            const meta = layerMeta[layer.key];
            const Icon = meta.icon;
            return (
              <React.Fragment key={layer.key}>
                <div className="contract-column">
                  <div className="contract-column-title"><Icon size={16} /><span>{meta.label}</span><small>{layer.nodes.length}</small></div>
                  <div className="contract-node-list">
                    {layer.nodes.length ? layer.nodes.map((node) => <ContractNodeCard node={node} key={node.id} />) : <div className="contract-empty">No node</div>}
                  </div>
                </div>
                {index < graphLayers.length - 1 ? <div className="contract-arrow"><ArrowRight size={16} /></div> : null}
              </React.Fragment>
            );
          })}
        </div>
      </section>

      <div className="metric-grid three">
        <div className="metric-card"><CheckCircle2 size={19} /><div><strong>{synchronizedNodes} synchronized</strong><span>Contracts aligned across layers</span></div></div>
        <div className="metric-card"><Network size={19} /><div><strong>{graph.edges.length} dependencies</strong><span>Mapped relationships</span></div></div>
        <div className="metric-card"><AlertTriangle size={19} /><div><strong>{graph.nodes.length - synchronizedNodes} need attention</strong><span>Modified or violated nodes</span></div></div>
      </div>
    </div>
  );

  const renderImpact = () => (
    <div className="view-stack">
      <section className="page-title-row">
        <div><span className="eyebrow">Change intelligence</span><h1>Measure the blast radius first.</h1><p>Describe a change. Sugio maps affected layers and asks before any mutation is allowed.</p></div>
      </section>

      <section className="content-card">
        <form className="impact-form" onSubmit={runImpact}>
          <label><span>Target entity</span><input value={targetEntity} onChange={(event) => setTargetEntity(event.target.value)} placeholder="Student, phone, POST /students…" /></label>
          <label className="wide"><span>Change request</span><textarea value={changeDescription} onChange={(event) => setChangeDescription(event.target.value)} rows={4} placeholder="Describe the requested application change" /></label>
          <LoadingButton className="primary-button" loading={busy === 'impact'} type="submit"><Zap size={16} /> Analyze impact</LoadingButton>
        </form>
      </section>

      {impactReport ? (
        <>
          <section className="impact-summary-card">
            <div><AppBadge tone={impactReport.risk_level === 'High' ? 'bad' : impactReport.risk_level === 'Medium' ? 'warn' : 'good'}>{impactReport.risk_level} risk</AppBadge><h2>{impactReport.summary}</h2></div>
            <div className="impact-count"><strong>{impactReport.affected_frontend.length + impactReport.affected_backend.length + impactReport.affected_apis.length + impactReport.affected_database.length + impactReport.affected_tests.length}</strong><span>affected nodes</span></div>
          </section>
          <div className="impact-grid">
            {[
              ['Frontend', impactReport.affected_frontend, Code2],
              ['API', impactReport.affected_apis, Server],
              ['Backend', impactReport.affected_backend, Terminal],
              ['Database', impactReport.affected_database, Database],
              ['Tests', impactReport.affected_tests, FlaskConical],
            ].map(([label, items, Icon]) => {
              const TypedIcon = Icon as React.ComponentType<{ size?: number }>;
              const typedItems = items as string[];
              return <div className="impact-layer" key={label as string}><div><TypedIcon size={17} /><strong>{label as string}</strong><span>{typedItems.length}</span></div>{typedItems.length ? typedItems.map((item) => <small key={item}>{item}</small>) : <small className="muted">No direct impact</small>}</div>;
            })}
          </div>
          {impactReport.explanations.length ? <section className="content-card"><div className="section-heading"><div><span className="eyebrow">Why this matters</span><h2>Agent reasoning summary</h2></div></div><div className="check-list">{impactReport.explanations.map((item) => <div key={item}><ArrowRight size={15} /><span>{item}</span></div>)}</div></section> : null}
        </>
      ) : <EmptyState icon={Zap} title="No analysis yet" text="Run an impact analysis to see which contracts a change could affect." />}
    </div>
  );

  const renderGit = () => (
    <div className="view-stack">
      <section className="page-title-row">
        <div><span className="eyebrow">Git safety</span><h1>Make risky work reversible.</h1><p>Create checkpoints before agent changes and restore a known state when verification fails.</p></div>
        <LoadingButton className="primary-button" loading={busy === 'checkpoint'} onClick={makeCheckpoint}><Plus size={16} /> New checkpoint</LoadingButton>
      </section>
      <div className="two-column git-layout">
        <section className="content-card">
          <div className="section-heading"><div><span className="eyebrow">Restore points</span><h2>Checkpoints</h2></div><button className="icon-button" onClick={() => void refreshGit()}><RefreshCw size={16} /></button></div>
          <div className="checkpoint-list">
            {checkpoints.length ? checkpoints.map((checkpoint) => (
              <div className="checkpoint-row" key={checkpoint.id}>
                <div className="checkpoint-mark"><GitBranch size={16} /></div>
                <div><strong>{checkpoint.name}</strong><span>{checkpoint.description || checkpoint.id}</span><small>{new Date(checkpoint.timestamp).toLocaleString()}</small></div>
                <LoadingButton className="secondary-button compact" loading={busy === `rollback:${checkpoint.id}`} onClick={() => rollback(checkpoint.id)}><RotateCcw size={14} /> Restore</LoadingButton>
              </div>
            )) : <EmptyState icon={GitBranch} title="No checkpoints" text="Create one before the next multi-file change." />}
          </div>
        </section>
        <section className="content-card diff-card">
          <div className="section-heading"><div><span className="eyebrow">Workspace</span><h2>Current diff</h2></div></div>
          <pre>{gitDiff || 'No tracked changes detected in the local project sandbox.'}</pre>
        </section>
      </div>
    </div>
  );

  const renderAssistant = () => (
    <div className="assistant-view">
      <section className="assistant-header">
        <div><span className="eyebrow">Sugio assistant</span><h1>Local engineering copilot</h1><p>Architecture-aware help grounded in the app you are building.</p></div>
        <select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="en">English</option><option value="ta">Tamil</option><option value="tanglish">Tanglish</option></select>
      </section>
      <section className="chat-panel">
        <div className="chat-messages">
          {messages.map((message) => (
            <div className={classNames('chat-message', message.role === 'user' && 'chat-user')} key={message.id}>
              <div className="chat-avatar">{message.role === 'assistant' ? <Bot size={16} /> : <User size={16} />}</div>
              <div><span>{message.role === 'assistant' ? 'Sugio' : 'You'}</span><p>{message.content}</p></div>
            </div>
          ))}
          {busy === 'chat' ? <div className="chat-message"><div className="chat-avatar"><Bot size={16} /></div><div><span>Sugio</span><p className="typing">Thinking locally<span>…</span></p></div></div> : null}
        </div>
        <form className="chat-composer" onSubmit={sendMessage}>
          <input value={chatInput} onChange={(event) => setChatInput(event.target.value)} placeholder="Ask about this project…" />
          <button type="submit" disabled={!chatInput.trim() || busy === 'chat'}><Send size={17} /></button>
        </form>
      </section>
    </div>
  );

  const renderCurrentView = () => {
    if (view === 'plan') return renderPlan();
    if (view === 'blueprint') return renderBlueprint();
    if (view === 'contracts') return renderContracts();
    if (view === 'impact') return renderImpact();
    if (view === 'git') return renderGit();
    return renderAssistant();
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Sparkles size={19} /></div>
          <div><strong>Sugio Labs</strong><span>Local dev agent</span></div>
        </div>

        <div className="project-switcher">
          <div className="project-icon">SL</div>
          <div><strong>{blueprint?.project_name ?? 'New project'}</strong><span>Local workspace</span></div>
          <ChevronRight size={16} />
        </div>

        <nav>
          <span className="nav-label">Workspace</span>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button className={classNames('nav-item', view === item.key && 'active')} onClick={() => setView(item.key)} key={item.key}>
                <Icon size={18} /><span><strong>{item.label}</strong><small>{item.hint}</small></span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-status">
          <div className="status-row"><span>{health?.status === 'healthy' ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />} Backend</span><strong>{health?.status ?? 'checking'}</strong></div>
          <div className="status-row"><span>{health?.ollama_online ? <Cpu size={15} /> : <WifiOff size={15} />} Local AI</span><strong>{health?.ollama_online ? 'Ollama' : 'Fallback'}</strong></div>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div className="topbar-context">
            <span>Workspace</span><ChevronRight size={14} /><strong>{navItems.find((item) => item.key === view)?.label}</strong>
          </div>
          <div className="topbar-actions">
            <AppBadge tone={isConnected ? 'good' : 'warn'}>{isConnected ? <Wifi size={13} /> : <WifiOff size={13} />}{isConnected ? 'Live events' : 'Reconnecting'}</AppBadge>
            <div className="hardware-pill"><Cpu size={15} /><span>{hardware ? `${hardware.ram_gb} GB · ${hardware.cpu_cores} cores` : 'Hardware scan'}</span></div>
          </div>
        </header>

        {error ? <div className="error-banner"><AlertTriangle size={16} /><span>{error}</span><button onClick={() => setError(null)}><X size={15} /></button></div> : null}

        <div className="workspace-grid">
          <main className="workspace-content">{busy === 'initialize' ? <div className="boot-state"><RefreshCw className="spin" size={24} /><span>Opening Sugio workspace…</span></div> : renderCurrentView()}</main>

          <aside className="activity-rail">
            <section className="rail-section">
              <div className="rail-heading"><span><Activity size={16} /> Live activity</span><AppBadge tone="neutral">{activities.length}</AppBadge></div>
              <div className="activity-list">
                {activities.length ? [...activities].reverse().slice(0, 8).map((item) => (
                  <div className="activity-item" key={item.id}>
                    <div className={classNames('activity-dot', `status-${item.status}`)}></div>
                    <div><strong>{item.step}</strong><span>{item.agent_name}</span><p>{item.details}</p></div>
                  </div>
                )) : <div className="rail-empty"><Activity size={18} /><span>Agent events will appear here.</span></div>}
              </div>
            </section>

            <section className="rail-section rail-contract">
              <div className="rail-heading"><span><ShieldCheck size={16} /> Contract health</span><strong>{contractHealth}%</strong></div>
              <div className="health-bar"><span style={{ width: `${contractHealth}%` }} /></div>
              <div className="mini-stats"><span><strong>{graph.nodes.length}</strong> nodes</span><span><strong>{graph.edges.length}</strong> links</span></div>
            </section>

            <section className="rail-section rail-privacy">
              <Lock size={17} />
              <div><strong>Human controlled</strong><span>Mutations stay gated behind explicit approval.</span></div>
            </section>
          </aside>
        </div>
      </div>

      {pendingPermission ? (
        <div className="modal-backdrop">
          <div className="permission-dialog">
            <div className="permission-icon"><ShieldCheck size={24} /></div>
            <AppBadge tone={pendingPermission.risk_level === 'high' || pendingPermission.risk_level === 'critical' ? 'bad' : 'warn'}>{pendingPermission.risk_level} risk</AppBadge>
            <h2>Permission required</h2>
            <p>Sugio wants to perform <strong>{pendingPermission.action.replaceAll('_', ' ')}</strong> on:</p>
            <code>{pendingPermission.target}</code>
            {pendingPermission.details?.change ? <div className="permission-change"><span>Requested change</span><p>{String(pendingPermission.details.change)}</p></div> : null}
            <div className="permission-actions">
              <button className="secondary-button" onClick={() => decidePermission('reject')} disabled={busy === 'permission'}>Reject</button>
              <button className="secondary-button" onClick={() => decidePermission('allow_once')} disabled={busy === 'permission'}>Allow once</button>
              <button className="primary-button" onClick={() => decidePermission('allow_for_project')} disabled={busy === 'permission'}><Check size={16} /> Allow for project</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

function ContractNodeCard({ node }: { node: ContractNode }) {
  return (
    <div className="contract-node">
      <div className="contract-node-top"><span className={classNames('node-status', `node-${node.status}`)}></span><AppBadge tone={node.status === 'synchronized' ? 'good' : node.status === 'violated' ? 'bad' : 'warn'}>{node.status.replace('_', ' ')}</AppBadge></div>
      <strong>{node.name}</strong>
      <code>{node.id}</code>
      {node.metadata?.fields ? <small>{Object.keys(node.metadata.fields).length} fields</small> : <small>{node.layer}</small>}
    </div>
  );
}
