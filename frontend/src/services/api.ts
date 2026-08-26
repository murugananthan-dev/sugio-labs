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

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

async function fetchWrapper<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      const errorText = await res.text().catch(() => 'Unknown Error');
      throw new Error(`API Error ${res.status}: ${errorText}`);
    }
    return res.json();
  } catch (err) {
    console.error(`Fetch failed for ${url}`, err);
    throw err;
  }
}

export async function fetchHealth(): Promise<HealthStatus> {
  return fetchWrapper<HealthStatus>(`${API_BASE}/health`);
}

export async function fetchHardware(): Promise<HardwareProfile> {
  return fetchWrapper<HardwareProfile>(`${API_BASE}/system/hardware`);
}

export async function startInterview(): Promise<{ question: RequirementQuestion }> {
  return fetchWrapper<{ question: RequirementQuestion }>(`${API_BASE}/interview/start`, { method: 'POST' });
}

export async function submitAnswer(
  questionId: string,
  answer: string
): Promise<{ status: 'next_question' | 'blueprint_ready'; question?: RequirementQuestion; blueprint?: ProjectBlueprint }> {
  return fetchWrapper(`${API_BASE}/interview/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question_id: questionId, answer }),
  });
}

export async function approveBlueprint(): Promise<{ status: string; blueprint: ProjectBlueprint; graph: ContractGraphData }> {
  return fetchWrapper(`${API_BASE}/blueprint/approve`, { method: 'POST' });
}

export async function fetchContractGraph(): Promise<ContractGraphData> {
  return fetchWrapper<ContractGraphData>(`${API_BASE}/contract-graph`);
}

export async function resetSampleGraph(): Promise<{ status: string; graph: ContractGraphData }> {
  return fetchWrapper(`${API_BASE}/contract-graph/sample`, { method: 'POST' });
}

export async function submitImpactAnalysis(
  targetEntity: string,
  changeDescription: string
): Promise<{ impact_report: ImpactReport; permission_request: PermissionRequest }> {
  return fetchWrapper(`${API_BASE}/impact-analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_entity: targetEntity, change_description: changeDescription }),
  });
}

export async function fetchPendingPermissions(): Promise<PermissionRequest[]> {
  return fetchWrapper<PermissionRequest[]>(`${API_BASE}/permissions/pending`);
}

export async function submitPermissionDecision(
  decision: PermissionResponse
): Promise<{ request_id: string; decision: string; granted: boolean }> {
  return fetchWrapper(`${API_BASE}/permissions/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(decision),
  });
}

export async function fetchSessionState(): Promise<any> {
  return fetchWrapper(`${API_BASE}/session/state`);
}

export async function sendChatMessage(
  message: string,
  language: string = 'en'
): Promise<{ reply: string; language: string }> {
  return fetchWrapper(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, language }),
  });
}

// Git Checkpoints & Rollback APIs
export async function fetchCheckpoints(): Promise<GitCheckpoint[]> {
  return fetchWrapper<GitCheckpoint[]>(`${API_BASE}/git/checkpoints`);
}

export async function createCheckpoint(name: string, description: string = ''): Promise<{ status: string; checkpoint: GitCheckpoint }> {
  return fetchWrapper(`${API_BASE}/git/checkpoint`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  });
}

export async function rollbackToCheckpoint(checkpointId: string): Promise<{ status: string; rolled_back_to: string }> {
  return fetchWrapper(`${API_BASE}/git/rollback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ checkpoint_id: checkpointId }),
  });
}

export async function fetchGitDiff(): Promise<{ diff: string }> {
  return fetchWrapper<{ diff: string }>(`${API_BASE}/git/diff`);
}

// Sandboxed Shell & MCP
export async function executeShellCommand(command: string): Promise<any> {
  return fetchWrapper(`${API_BASE}/shell/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  });
}

export async function fetchMCPTools(): Promise<MCPToolDefinition[]> {
  return fetchWrapper<MCPToolDefinition[]>(`${API_BASE}/mcp/tools`);
}
