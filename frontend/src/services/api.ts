import {
  HealthStatus,
  HardwareProfile,
  RequirementQuestion,
  ProjectBlueprint,
  ContractGraphData,
  ImpactReport,
  PermissionRequest,
  PermissionResponse,
  GitCheckpoint,
  MCPToolDefinition,
} from '../types';

const API_BASE = 'http://127.0.0.1:8000/api/v1';
const WS_URL = 'ws://127.0.0.1:8000/ws';

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Failed to fetch health status');
  return res.json();
}

export async function fetchHardware(): Promise<HardwareProfile> {
  const res = await fetch(`${API_BASE}/system/hardware`);
  if (!res.ok) throw new Error('Failed to fetch hardware profile');
  return res.json();
}

export async function startInterview(): Promise<{ question: RequirementQuestion }> {
  const res = await fetch(`${API_BASE}/interview/start`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to start interview');
  return res.json();
}

export async function submitAnswer(
  questionId: string,
  answer: string
): Promise<{ status: 'next_question' | 'blueprint_ready'; question?: RequirementQuestion; blueprint?: ProjectBlueprint }> {
  const res = await fetch(`${API_BASE}/interview/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question_id: questionId, answer }),
  });
  if (!res.ok) throw new Error('Failed to submit answer');
  return res.json();
}

export async function approveBlueprint(): Promise<{ status: string; blueprint: ProjectBlueprint; graph: ContractGraphData }> {
  const res = await fetch(`${API_BASE}/blueprint/approve`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to approve blueprint');
  return res.json();
}

export async function fetchContractGraph(): Promise<ContractGraphData> {
  const res = await fetch(`${API_BASE}/contract-graph`);
  if (!res.ok) throw new Error('Failed to fetch contract graph');
  return res.json();
}

export async function resetSampleGraph(): Promise<{ status: string; graph: ContractGraphData }> {
  const res = await fetch(`${API_BASE}/contract-graph/sample`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to reset sample graph');
  return res.json();
}

export async function submitImpactAnalysis(
  targetEntity: string,
  changeDescription: string
): Promise<{ impact_report: ImpactReport; permission_request: PermissionRequest }> {
  const res = await fetch(`${API_BASE}/impact-analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_entity: targetEntity, change_description: changeDescription }),
  });
  if (!res.ok) throw new Error('Failed to execute impact analysis');
  return res.json();
}

export async function fetchPendingPermissions(): Promise<PermissionRequest[]> {
  const res = await fetch(`${API_BASE}/permissions/pending`);
  if (!res.ok) throw new Error('Failed to fetch pending permissions');
  return res.json();
}

export async function submitPermissionDecision(
  decision: PermissionResponse
): Promise<{ request_id: string; decision: string; granted: boolean }> {
  const res = await fetch(`${API_BASE}/permissions/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(decision),
  });
  if (!res.ok) throw new Error('Failed to submit permission decision');
  return res.json();
}

export async function fetchSessionState(): Promise<any> {
  const res = await fetch(`${API_BASE}/session/state`);
  if (!res.ok) throw new Error('Failed to fetch session state');
  return res.json();
}

export async function sendChatMessage(
  message: string,
  language: string = 'en'
): Promise<{ reply: string; language: string }> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, language }),
  });
  if (!res.ok) throw new Error('Failed to send chat message');
  return res.json();
}

// Git Checkpoints & Rollback APIs
export async function fetchCheckpoints(): Promise<GitCheckpoint[]> {
  const res = await fetch(`${API_BASE}/git/checkpoints`);
  if (!res.ok) throw new Error('Failed to fetch checkpoints');
  return res.json();
}

export async function createCheckpoint(name: string, description: string = ''): Promise<{ status: string; checkpoint: GitCheckpoint }> {
  const res = await fetch(`${API_BASE}/git/checkpoint`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) throw new Error('Failed to create checkpoint');
  return res.json();
}

export async function rollbackToCheckpoint(checkpointId: string): Promise<{ status: string; rolled_back_to: string }> {
  const res = await fetch(`${API_BASE}/git/rollback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ checkpoint_id: checkpointId }),
  });
  if (!res.ok) throw new Error('Failed to execute rollback');
  return res.json();
}

export async function fetchGitDiff(): Promise<{ diff: string }> {
  const res = await fetch(`${API_BASE}/git/diff`);
  if (!res.ok) throw new Error('Failed to fetch git diff');
  return res.json();
}

// Sandboxed Shell & MCP
export async function executeShellCommand(command: string): Promise<any> {
  const res = await fetch(`${API_BASE}/shell/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  });
  if (!res.ok) throw new Error('Failed to execute shell command');
  return res.json();
}

export async function fetchMCPTools(): Promise<MCPToolDefinition[]> {
  const res = await fetch(`${API_BASE}/mcp/tools`);
  if (!res.ok) throw new Error('Failed to fetch MCP tools');
  return res.json();
}

export function createWebSocketConnection(onMessage: (data: any) => void): WebSocket {
  const ws = new WebSocket(WS_URL);
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('Error parsing WebSocket message', e);
    }
  };
  return ws;
}
