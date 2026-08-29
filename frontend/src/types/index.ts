// ============================================================================
// PERMISSION SYSTEM
// ============================================================================

export type PermissionAction =
  | 'read_file'
  | 'write_file'
  | 'delete_file'
  | 'execute_command'
  | 'database_migration'
  | 'git_operation'
  | 'connect_tool'
  | 'network_access';

export type PermissionDecision = 'allow_once' | 'allow_for_project' | 'reject';

export interface PermissionRequest {
  id: string;
  action: PermissionAction;
  target: string;
  details: Record<string, any>;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  session_id?: string;
}

export interface PermissionResponse {
  request_id: string;
  decision: PermissionDecision;
  reason?: string;
}

// ============================================================================
// CONTRACT GRAPH
// ============================================================================

export type ContractNodeType =
  | 'requirement'
  | 'frontend'
  | 'api'
  | 'backend'
  | 'database'
  | 'test';

export type ContractNodeStatus =
  | 'synchronized'
  | 'modified'
  | 'violated'
  | 'pending_approval';

export interface ContractNode {
  id: string;
  name: string;
  layer: string;
  node_type: ContractNodeType;
  metadata: Record<string, any>;
  status: ContractNodeStatus;
}

export interface ContractEdge {
  source: string;
  target: string;
  relation_type: string;
  metadata?: Record<string, any>;
}

export interface ContractGraphData {
  nodes: ContractNode[];
  edges: ContractEdge[];
}

export interface ContractViolation {
  source_node: string;
  target_node: string;
  source_field: string;
  expected_field: string;
  endpoint_or_module: string;
  description: string;
}

// ============================================================================
// IMPACT ANALYSIS
// ============================================================================

export interface ImpactReport {
  summary: string;
  affected_frontend: string[];
  affected_backend: string[];
  affected_apis: string[];
  affected_database: string[];
  affected_tests: string[];
  violations: ContractViolation[];
  risk_level: 'Low' | 'Medium' | 'High';
  explanations: string[];
}

// ============================================================================
// REQUIREMENT INTERVIEW
// ============================================================================

export interface RequirementQuestion {
  id: string;
  question: string;
  category: string;
  options: string[];
  recommended_option?: string;
  recommendation_reason?: string;
  current_answer?: string;
}

// ============================================================================
// BLUEPRINT
// ============================================================================

export interface ProjectBlueprint {
  project_name: string;
  objective: string;
  user_roles: string[];
  features: string[];
  functional_requirements: string[];
  non_functional_requirements: string[];
  selected_stack: Record<string, string>;
  architecture_summary: string;
  frontend_modules: Array<{ name: string; path: string; purpose: string }>;
  backend_modules: Array<{ name: string; path: string; purpose: string }>;
  api_endpoints: Array<{ method: string; path: string; description: string }>;
  db_schema: Array<{ table: string; columns: Array<{ name: string; type: string; constraints: string }> }>;
  folder_structure: string[];
  testing_strategy: string;
  development_steps: string[];
  risks: string[];
  approved: boolean;
}

// ============================================================================
// EXECUTION PLAN — matches backend schemas.py exactly
// ============================================================================

export type ExecutionStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'waiting_permission';

export interface ExecutionStep {
  id: string;
  title: string;
  description: string;
  files_to_read: string[];
  files_to_modify: string[];
  commands: string[];
  dependencies: string[];
  risk_level: string;
  requires_permission: boolean;
  status: ExecutionStatus;
  result_details?: string | null;
}

export interface ExecutionPlan {
  blueprint_context: string;
  ordered_steps: ExecutionStep[];
  overall_risk: string;
  estimated_affected_files: number;
  validation_strategy: string;
}

export interface ExecutionResult {
  step_id: string;
  success: boolean;
  output?: string | null;
  error?: string | null;
}

// Execution approval status values returned by the backend
export type ExecutionApprovalStatus =
  | 'NONE'
  | 'WAITING_FOR_EXECUTION_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'EDIT';

// ============================================================================
// ACTIVITY LOG
// ============================================================================

export interface AgentActivityLog {
  id: string;
  step: string;
  agent_name: string;
  status: 'running' | 'completed' | 'failed' | 'waiting_permission';
  details: string;
  timestamp: string;
}

// ============================================================================
// SYSTEM
// ============================================================================

export interface HardwareProfile {
  ram_gb: number;
  cpu_cores: number;
  os: string;
  recommended_model: string;
  recommended_tier: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  ollama_online: boolean;
  local_models_detected: string[];
}

export interface GitCheckpoint {
  id: string;
  name: string;
  commit_hash: string;
  timestamp: string;
  description: string;
}

export interface MCPToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, any>;
}

// ============================================================================
// SESSION STATE — mirrors get_session_state() on the backend
// ============================================================================

export interface SessionState {
  session_id: string;
  requirements_complete: boolean;
  current_question: string | null;
  has_blueprint: boolean;
  blueprint: ProjectBlueprint | null;
  approval_status: string;
  has_execution_plan: boolean;
  execution_plan: ExecutionPlan | null;
  execution_approval_status: ExecutionApprovalStatus;
  current_step_index: number;
  execution_results: ExecutionResult[];
  checkpoint_id: string | null;
  graph: ContractGraphData;
  pending_permissions: PermissionRequest[];
  hardware: HardwareProfile;
  activity_logs?: AgentActivityLog[];
  checkpoints?: GitCheckpoint[];
}

// ============================================================================
// PLANNING CHAT RESPONSE — returned by POST /chat/planning
// ============================================================================

export interface PlanningChatResponse {
  status: 'planning' | 'blocked' | 'error';
  requirements_complete: boolean;
  current_question: string | null;
  approval_status: string;
  blueprint?: ProjectBlueprint;
}

// ============================================================================
// BLUEPRINT DECISION RESPONSE — returned by POST /blueprint/decision
// ============================================================================

export interface BlueprintDecisionResponse {
  status: string;
  approval_status: string;
}

// ============================================================================
// EXECUTION DECISION RESPONSE — returned by POST /execution/decision
// ============================================================================

export interface ExecutionDecisionResponse {
  status: string;
  execution_approval_status: ExecutionApprovalStatus;
}
