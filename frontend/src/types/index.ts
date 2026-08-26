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

export interface RequirementQuestion {
  id: string;
  question: string;
  category: string;
  options: string[];
  recommended_option?: string;
  recommendation_reason?: string;
  current_answer?: string;
}

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
  db_schema: Array<{ table: string; columns: string[] }>;
  folder_structure: string[];
  testing_strategy: string;
  development_steps: string[];
  risks: string[];
  approved: boolean;
}

export interface AgentActivityLog {
  id: string;
  step: string;
  agent_name: string;
  status: 'running' | 'completed' | 'failed' | 'waiting_permission';
  details: string;
  timestamp: string;
}

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
