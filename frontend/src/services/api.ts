import {
  HealthStatus,
  HardwareProfile,
  ContractGraphData,
  ImpactReport,
  PermissionRequest,
  PermissionResponse,
  GitCheckpoint,
  MCPToolDefinition,
  PlanningChatResponse,
  BlueprintDecisionResponse,
  ExecutionDecisionResponse,
  ProjectWorkspace,
  ProjectScanResult,
  SessionState,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

// ============================================================================
// CORE FETCH WRAPPER
// ============================================================================

async function fetchWrapper<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        detail = body?.detail || body?.message || JSON.stringify(body);
      } catch {
        detail = await res.text().catch(() => `HTTP ${res.status}`);
      }
      throw new Error(detail);
    }
    return res.json();
  } catch (err) {
    if (err instanceof TypeError && err.message.includes('fetch')) {
      throw new Error('Cannot connect to backend. Is the server running?');
    }
    throw err;
  }
}

function postJson<T>(url: string, body: unknown): Promise<T> {
  return fetchWrapper<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// ============================================================================
// 1. HEALTH & SYSTEM
// ============================================================================

export async function fetchHealth(): Promise<HealthStatus> {
  return fetchWrapper<HealthStatus>(`${API_BASE}/health`);
}

export async function fetchHardware(): Promise<HardwareProfile> {
  return fetchWrapper<HardwareProfile>(`${API_BASE}/system/hardware`);
}

// ============================================================================
// 2. REQUIREMENT INTERVIEW (POST /chat/planning)
//
// The backend uses a single conversational endpoint.
// startPlanning() — sends the initial project idea to begin the interview.
// submitPlanningMessage() — sends subsequent answers / messages.
// Both return PlanningChatResponse which contains current_question or signals
// blueprint_ready via requirements_complete + blueprint fields.
// ============================================================================

export async function startPlanning(
  projectIdea: string,
  language: string = 'en'
): Promise<PlanningChatResponse> {
  return postJson<PlanningChatResponse>(`${API_BASE}/chat/planning`, {
    message: projectIdea,
    language,
  });
}

export async function submitPlanningMessage(
  message: string,
  language: string = 'en'
): Promise<PlanningChatResponse> {
  return postJson<PlanningChatResponse>(`${API_BASE}/chat/planning`, {
    message,
    language,
  });
}

// ============================================================================
// 3. BLUEPRINT DECISION (POST /blueprint/decision)
//
// decision: "APPROVE" | "REJECT" | "EDIT"
// modifications: optional free-text edit instructions (only for EDIT)
// ============================================================================

export async function submitBlueprintDecision(
  decision: 'APPROVE' | 'REJECT' | 'EDIT',
  modifications?: string
): Promise<BlueprintDecisionResponse> {
  return postJson<BlueprintDecisionResponse>(`${API_BASE}/blueprint/decision`, {
    decision,
    modifications: modifications ?? null,
  });
}

// ============================================================================
// 4. EXECUTION DECISION (POST /execution/decision)
//
// decision: "APPROVE" | "REJECT" | "EDIT" | "FIX" | "RETRY" | "ROLLBACK"
// ============================================================================

export async function submitExecutionDecision(
  decision: 'APPROVE' | 'REJECT' | 'EDIT' | 'FIX' | 'RETRY' | 'ROLLBACK',
  modifications?: string
): Promise<ExecutionDecisionResponse> {
  return postJson<ExecutionDecisionResponse>(`${API_BASE}/execution/decision`, {
    decision,
    modifications,
  });
}

// ============================================================================
// 5. SESSION STATE (GET /session/state)
//
// Returns full supervisor session including execution plan, graph, etc.
// Use for initial page load / reconnect recovery. Not for polling during
// normal flow.
// ============================================================================

export async function fetchSessionState(): Promise<SessionState> {
  return fetchWrapper<SessionState>(`${API_BASE}/session/state`);
}

// ============================================================================
// 5.5 WORKSPACE IMPORT & CREATE
// ============================================================================

export async function importWorkspace(path: string): Promise<{ status: string; scan_result: ProjectScanResult }> {
  return postJson(`${API_BASE}/workspace/import`, { path });
}

export async function createWorkspace(name: string, parentPath: string): Promise<{ status: string; workspace: ProjectWorkspace }> {
  return postJson(`${API_BASE}/workspace/create`, { name, parent_path: parentPath });
}

// ============================================================================
// 6. CONTRACT GRAPH
// ============================================================================

export async function fetchContractGraph(): Promise<ContractGraphData> {
  return fetchWrapper<ContractGraphData>(`${API_BASE}/contract-graph`);
}

export async function resetSampleGraph(): Promise<{ status: string; graph: ContractGraphData }> {
  return fetchWrapper(`${API_BASE}/contract-graph/sample`, { method: 'POST' });
}

// ============================================================================
// 7. IMPACT ANALYSIS
// ============================================================================

export async function submitImpactAnalysis(
  targetEntity: string,
  changeDescription: string
): Promise<{ impact_report: ImpactReport; permission_request: PermissionRequest }> {
  return postJson(`${API_BASE}/impact-analysis`, {
    target_entity: targetEntity,
    change_description: changeDescription,
  });
}

// ============================================================================
// 8. HUMAN-IN-THE-LOOP PERMISSION GATEWAY
// ============================================================================

export async function fetchPendingPermissions(): Promise<PermissionRequest[]> {
  return fetchWrapper<PermissionRequest[]>(`${API_BASE}/permissions/pending`);
}

export async function submitPermissionDecision(
  decision: PermissionResponse
): Promise<{ request_id: string; decision: string; granted: boolean }> {
  return postJson(`${API_BASE}/permissions/decision`, decision);
}

// ============================================================================
// 9. GIT CHECKPOINTS & ROLLBACK
// ============================================================================

export async function fetchCheckpoints(): Promise<GitCheckpoint[]> {
  return fetchWrapper<GitCheckpoint[]>(`${API_BASE}/git/checkpoints`);
}

export async function createCheckpoint(
  name: string,
  description: string = ''
): Promise<{ status: string; checkpoint: GitCheckpoint }> {
  return postJson(`${API_BASE}/git/checkpoint`, { name, description });
}

export async function rollbackToCheckpoint(
  checkpointId: string
): Promise<{ status: string; rolled_back_to: string }> {
  return postJson(`${API_BASE}/git/rollback`, { checkpoint_id: checkpointId });
}

export async function fetchGitDiff(): Promise<{ diff: string }> {
  return fetchWrapper<{ diff: string }>(`${API_BASE}/git/diff`);
}

// ============================================================================
// 10. SANDBOXED SHELL & MCP
// ============================================================================

export async function executeShellCommand(
  command: string,
  timeoutSeconds: number = 60
): Promise<any> {
  return postJson(`${API_BASE}/shell/execute`, {
    command,
    timeout_seconds: timeoutSeconds,
  });
}

export async function fetchMCPTools(): Promise<MCPToolDefinition[]> {
  return fetchWrapper<MCPToolDefinition[]>(`${API_BASE}/mcp/tools`);
}

// ============================================================================
// LEGACY / COMPATIBILITY ALIASES
// (kept to avoid breaking existing imports — redirect to correct endpoints)
// ============================================================================

/** @deprecated Use submitPlanningMessage() instead */
export const startInterview = (language?: string) =>
  startPlanning('Hello, I want to start a new project.', language);

/** @deprecated Use submitPlanningMessage() instead */
export const submitAnswer = (_questionId: string, answer: string, language?: string) =>
  submitPlanningMessage(answer, language);

/** @deprecated Use submitBlueprintDecision("APPROVE") instead */
export const approveBlueprint = () => submitBlueprintDecision('APPROVE');

/**
 * AI Assistant chat — used by ChatAssistant.tsx.
 * Routes through /chat/planning and adapts the response to the
 * { reply, language } shape the component expects.
 */
export async function sendChatMessage(
  message: string,
  language: string = 'en'
): Promise<{ reply: string; language: string }> {
  const res = await submitPlanningMessage(message, language);
  // Derive a human-readable reply from whatever the planning turn returns
  let reply = '';
  if (res.current_question) {
    reply = res.current_question;
  } else if (res.requirements_complete && res.blueprint) {
    reply = `Your project blueprint for "${res.blueprint.project_name}" is ready! Please go to the Architecture Blueprint tab to review and approve it.`;
  } else if (res.status === 'blocked') {
    reply = 'A blueprint or execution plan is currently waiting for your approval. Please review it in the appropriate tab.';
  } else {
    reply = 'I processed your message. Please check the Requirement Wizard or Blueprint tabs for the latest status.';
  }
  return { reply, language };
}
