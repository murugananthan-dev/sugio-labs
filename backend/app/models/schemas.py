from enum import Enum
from typing import List, Dict, Any, Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# ============================================================================
# 1. PERMISSION SYSTEM SCHEMAS
# ============================================================================

class PermissionAction(str, Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    EXECUTE_COMMAND = "execute_command"
    DATABASE_MIGRATION = "database_migration"
    GIT_OPERATION = "git_operation"
    CONNECT_TOOL = "connect_tool"
    NETWORK_ACCESS = "network_access"

class PermissionDecision(str, Enum):
    ALLOW_ONCE = "allow_once"
    ALLOW_FOR_PROJECT = "allow_for_project"
    REJECT = "reject"

class PermissionRequest(BaseModel):
    id: str = Field(..., description="Unique request identifier")
    action: PermissionAction = Field(..., description="Type of action requested")
    target: str = Field(..., description="Target file path, command, or resource")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed action parameters or diff preview")
    risk_level: str = Field(default="medium", description="Risk level: low, medium, high, critical")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = Field(default=None, description="Active project session ID")

class PermissionResponse(BaseModel):
    request_id: str = Field(..., description="ID matching the PermissionRequest")
    decision: PermissionDecision = Field(..., description="User decision")
    reason: Optional[str] = Field(default=None, description="Optional rejection reason or feedback")

# ============================================================================
# 2. CONTRACT GRAPH SCHEMAS
# ============================================================================

class ContractNodeType(str, Enum):
    REQUIREMENT = "requirement"
    FRONTEND = "frontend"
    API = "api"
    BACKEND = "backend"
    DATABASE = "database"
    TEST = "test"

class ContractNodeStatus(str, Enum):
    SYNCHRONIZED = "synchronized"
    MODIFIED = "modified"
    VIOLATED = "violated"
    PENDING_APPROVAL = "pending_approval"

class ContractNode(BaseModel):
    id: str = Field(..., description="Unique node ID e.g. req:phone, fe:StudentForm, api:post_students")
    name: str = Field(..., description="Human readable label")
    layer: str = Field(..., description="Layer category e.g. Frontend, API, Backend, Database, Test, Requirement")
    node_type: ContractNodeType = Field(..., description="Enum type of node")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Field names, types, endpoints, schemas, etc.")
    status: ContractNodeStatus = Field(default=ContractNodeStatus.SYNCHRONIZED)

class ContractEdge(BaseModel):
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relation_type: str = Field(default="depends_on", description="Relation: depends_on, invokes, validates, persists, tests")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ContractGraphData(BaseModel):
    nodes: List[ContractNode] = Field(default_factory=list)
    edges: List[ContractEdge] = Field(default_factory=list)

class ContractViolation(BaseModel):
    source_node: str = Field(..., description="Node where drift originates")
    target_node: str = Field(..., description="Target node expecting different contract")
    source_field: str = Field(..., description="Field in source")
    expected_field: str = Field(..., description="Field expected by target")
    endpoint_or_module: str = Field(..., description="Affected route or layer")
    description: str = Field(..., description="Human readable explanation")

# ============================================================================
# 3. REQUIREMENT GATHERING & BLUEPRINT SCHEMAS
# ============================================================================

class RequirementQuestion(BaseModel):
    id: str = Field(..., description="Question index or code e.g. Q1_PROJECT_TYPE")
    question: str = Field(..., description="Question prompt")
    category: str = Field(default="general", description="architecture, tech_stack, features, database, auth")
    options: List[str] = Field(default_factory=list, description="Preset selectable choices")
    recommended_option: Optional[str] = Field(default=None, description="AI recommended choice")
    recommendation_reason: Optional[str] = Field(default=None, description="Why this recommendation is best")
    current_answer: Optional[str] = Field(default=None, description="User selected or custom answer")

class RequirementSpec(BaseModel):
    project_name: str = Field(default="New Project")
    project_type: str = Field(default="full-stack", description="frontend, backend, database_api, full-stack")
    target_users: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    auth_required: bool = Field(default=False)
    roles: List[str] = Field(default_factory=lambda: ["user", "admin"])
    frontend_stack: str = Field(default="React (TypeScript + Vite)")
    backend_stack: str = Field(default="FastAPI (Python)")
    database_stack: str = Field(default="PostgreSQL")
    api_type: str = Field(default="REST")
    testing_stack: str = Field(default="Pytest + Vitest")
    ui_preferences: str = Field(default="Dark Modern Glassmorphic")
    extra_requirements: Optional[str] = Field(default=None)
    
class PartialRequirementExtraction(BaseModel):
    """Used for structured output from the LLM during the interview phase."""
    extracted_spec: RequirementSpec = Field(..., description="The current known project requirements.")
    missing_fields: List[str] = Field(default_factory=list, description="Fields that still need user clarification.")
    is_complete: bool = Field(default=False, description="True if enough info exists to generate a comprehensive blueprint.")
    next_question: str = Field(default="", description="The exact question to ask the user next, based on missing fields.")

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_PERMISSION = "waiting_permission"

class ExecutionStep(BaseModel):
    id: str = Field(..., description="Step identifier, e.g., 'setup_db'")
    title: str = Field(..., description="Short title of the step")
    description: str = Field(..., description="Detailed explanation of what this step accomplishes")
    files_to_read: List[str] = Field(default_factory=list, description="Paths of files to inspect before modification")
    files_to_modify: List[str] = Field(default_factory=list, description="Paths of files to create, update, or delete")
    commands: List[str] = Field(default_factory=list, description="Shell commands required for this step")
    dependencies: List[str] = Field(default_factory=list, description="IDs of steps that must complete before this one")
    risk_level: str = Field(default="low", description="low, medium, high")
    requires_permission: bool = Field(default=True, description="Whether this step requires user permission to execute")
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING)
    result_details: Optional[str] = Field(default=None, description="Output or error details from execution")

class ExecutionPlan(BaseModel):
    blueprint_context: str = Field(..., description="Summary of the blueprint driving this plan")
    ordered_steps: List[ExecutionStep] = Field(default_factory=list, description="Sequential steps to execute")
    overall_risk: str = Field(default="medium", description="Overall risk of the execution plan")
    estimated_affected_files: int = Field(default=0, description="Number of files expected to change")
    validation_strategy: str = Field(..., description="How the execution will be validated (e.g., specific pytest commands)")

class ExecutionResult(BaseModel):
    step_id: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None

# ============================================================================
# 3b. EXECUTION ENGINE — GENERATED FILE CHANGE & FAILURE REPORTING
# ============================================================================

class FileOperation(str, Enum):
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    # DELETE is intentionally absent — not permitted in Phase 6

class GeneratedFileChange(BaseModel):
    """Structured file-write intent produced by the CodingAgent via local Ollama."""
    path: str = Field(..., description="Sandbox-relative file path, e.g. 'src/models/student.py'")
    operation: FileOperation = Field(..., description="CREATE or MODIFY only")
    content: str = Field(..., description="Full file content to write")
    reason: str = Field(default="", description="Why this file change is needed")

class FailureSuggestion(str, Enum):
    FIX = "FIX"
    RETRY = "RETRY"
    ROLLBACK = "ROLLBACK"

class ExecutionFailureReport(BaseModel):
    """Returned when execution fails mid-plan. Suggests next user action."""
    failed_step_id: str
    reason: str
    checkpoint_id: Optional[str] = None
    suggestion: FailureSuggestion = FailureSuggestion.ROLLBACK
    validation_output: Optional[str] = None
    validation_stderr: Optional[str] = None

class AppState(TypedDict):
    """LangGraph state for the full workflow (Planning & Execution)."""
    session_id: str
    messages: Annotated[List[Any], add_messages]
    detected_language: str
    requirements: RequirementSpec
    requirements_complete: bool
    current_question: Optional[str]
    blueprint: Optional['ProjectBlueprint']
    approval_status: str  # WAITING_FOR_APPROVAL, APPROVED, REJECTED, EDIT
    
    execution_plan: Optional[ExecutionPlan]
    execution_approval_status: str  # NONE, WAITING_FOR_EXECUTION_APPROVAL, APPROVED, REJECTED, EDIT
    current_step_index: int
    execution_results: List[ExecutionResult]
    git_checkpoint_id: Optional[str]  # renamed from checkpoint_id to avoid LangGraph reserved channel conflict
    errors: List[str]

class ProjectBlueprint(BaseModel):
    project_name: str
    objective: str
    user_roles: List[str]
    features: List[str]
    functional_requirements: List[str]
    non_functional_requirements: List[str]
    selected_stack: Dict[str, str]
    architecture_summary: str
    frontend_modules: List[Dict[str, Any]]
    backend_modules: List[Dict[str, Any]]
    api_endpoints: List[Dict[str, Any]]
    db_schema: List[Dict[str, Any]]
    folder_structure: List[str]
    testing_strategy: str
    development_steps: List[str]
    risks: List[str]
    approved: bool = Field(default=False)

# ============================================================================
# 4. IMPACT ANALYSIS & VERIFICATION SCHEMAS
# ============================================================================

class ImpactReport(BaseModel):
    summary: str
    affected_frontend: List[str] = Field(default_factory=list)
    affected_backend: List[str] = Field(default_factory=list)
    affected_apis: List[str] = Field(default_factory=list)
    affected_database: List[str] = Field(default_factory=list)
    affected_tests: List[str] = Field(default_factory=list)
    violations: List[ContractViolation] = Field(default_factory=list)
    risk_level: str = Field(default="Low", description="Low, Medium, High")
    explanations: List[str] = Field(default_factory=list)

class VerificationResult(BaseModel):
    requirement_name: str
    code_generated: bool = True
    frontend_build: bool = True
    backend_startup: bool = True
    api_test: bool = True
    database_check: bool = True
    contract_validation: bool = True
    tests_passed: int = 0
    total_tests: int = 0
    all_passed: bool = False
    details: List[str] = Field(default_factory=list)

# ============================================================================
# 5. WEBSOCKET & ACTIVITY LOG SCHEMAS
# ============================================================================

class WSMessageType(str, Enum):
    CHAT_MESSAGE = "chat_message"
    QUESTION_PROMPT = "question_prompt"
    BLUEPRINT_READY = "blueprint_ready"
    PERMISSION_REQUIRED = "permission_required"
    IMPACT_ANALYSIS = "impact_analysis"
    GRAPH_UPDATE = "graph_update"
    ACTIVITY_LOG = "activity_log"
    VOICE_UPDATE = "voice_update"
    VERIFICATION_RESULT = "verification_result"
    ERROR_ALERT = "error_alert"

class WSMessage(BaseModel):
    type: WSMessageType
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AgentActivityLog(BaseModel):
    id: str
    step: str
    agent_name: str
    status: str = Field(default="running", description="running, completed, failed, waiting_permission")
    details: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
