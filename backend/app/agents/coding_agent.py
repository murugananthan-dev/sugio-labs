"""
CodingAgent — Real End-to-End Safe Execution Engine
====================================================
Implements one ExecutionStep at a time:

  1. Ollama preflight — fail safely before any mutation if offline.
  2. Dependency gate — skip step if a dependency step FAILED.
  3. Permission gate — FSTool/ShellTool carry their own single permission
     check. Do NOT call is_action_permitted() here before calling the tool;
     that would consume an ALLOW_ONCE grant twice and break the single-use
     contract. Let the tool raise PermissionDeniedError, catch it, and
     surface a pending permission request to the UI.
  4. MODIFY reads the existing file first, includes it in the model context.
  5. CREATE verifies the target path does not already exist (no silent overwrite).
  6. Generated changes are strictly validated (path, operation, content, sandbox).
  7. Writes go through FSTool.write_file() only — the sole safe write path.
  8. Step status advances: PENDING → IN_PROGRESS → COMPLETED | FAILED.
  9. DELETE is not supported. Any model output requesting DELETE is rejected.
"""
import json
import logging
from pathlib import Path
from typing import List, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from ..models.schemas import (
    AppState,
    ExecutionStatus,
    ExecutionResult,
    ExecutionFailureReport,
    FailureSuggestion,
    GeneratedFileChange,
    FileOperation,
    PermissionAction,
)
from .base import local_llm
from ..tools.fs import FSTool
from ..permissions.manager import (
    permission_manager,
    PermissionDeniedError,
    SandboxSecurityError,
)
from ..config import settings

logger = logging.getLogger("sugio_labs.agents.coding_agent")

# ---------------------------------------------------------------------------
# Structured output schema sent to Ollama
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a Safe Coding Agent for Sugio Labs.
Your job is to implement exactly ONE step from an ExecutionPlan.

RULES (NON-NEGOTIABLE):
- Output ONLY a JSON array of file change objects — no prose, no markdown fences.
- Each object must have: "path" (string), "operation" ("CREATE" or "MODIFY"), \
"content" (string), "reason" (string).
- DELETE is NEVER permitted. Do not include it.
- "path" must be a relative sandbox path (e.g. "src/models/student.py"). \
Never use absolute paths or path traversal.
- "content" must be the complete, runnable file content — no truncation, \
no ellipsis, no TODO stubs.
- If a file must be modified, the current file content will be included in \
the context — you MUST produce the full updated content.
- If you cannot implement the step safely, return an empty array [].

OUTPUT FORMAT (strict):
[
  {
    "path": "src/models/student.py",
    "operation": "CREATE",
    "content": "...",
    "reason": "Initial Student model"
  }
]
"""

_MAX_EXISTING_FILE_CHARS = 8000  # trim very large files before sending to model


# ---------------------------------------------------------------------------
# Parse + validate raw LLM output → List[GeneratedFileChange]
# ---------------------------------------------------------------------------

def _parse_llm_output(
    raw: str,
    sandbox_root: Path,
) -> List[GeneratedFileChange]:
    """
    Parses the model's raw text output into validated GeneratedFileChange objects.
    Rejects:
     - malformed JSON
     - missing required fields
     - unsupported operations (DELETE or unknown)
     - empty / whitespace-only content
     - paths containing '..' or absolute paths
     - paths that would escape the sandbox (SandboxSecurityError)
    """
    # Strip markdown code fences if the model wrapped the output anyway
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first and last fence lines
        inner = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(inner).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model output is not valid JSON: {exc}\nRaw output:\n{raw[:500]}")

    if not isinstance(data, list):
        raise ValueError(f"Model output must be a JSON array, got {type(data).__name__}")

    changes: List[GeneratedFileChange] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} is not a JSON object: {item!r}")

        # Required field presence
        for field in ("path", "operation", "content"):
            if field not in item:
                raise ValueError(f"Item {i} missing required field '{field}': {item!r}")

        raw_path: str = item["path"]
        raw_op: str = item["operation"]
        content: str = item.get("content", "")
        reason: str = item.get("reason", "")

        # --- path validation ---
        if not raw_path or not isinstance(raw_path, str):
            raise ValueError(f"Item {i}: 'path' must be a non-empty string")
        if ".." in raw_path or raw_path.startswith("/") or (len(raw_path) > 1 and raw_path[1] == ":"):
            raise ValueError(f"Item {i}: 'path' must be sandbox-relative (no '..' or absolute): {raw_path!r}")
        # Check sandbox containment via the permission manager
        try:
            permission_manager.validate_path(raw_path, sandbox_root)
        except SandboxSecurityError as exc:
            raise ValueError(f"Item {i}: path '{raw_path}' fails sandbox check: {exc}")

        # --- operation validation ---
        try:
            op = FileOperation(raw_op.upper())
        except ValueError:
            raise ValueError(
                f"Item {i}: unsupported operation '{raw_op}'. Only CREATE and MODIFY are allowed."
            )

        # --- content validation ---
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"Item {i}: 'content' must be a non-empty string")

        changes.append(
            GeneratedFileChange(path=raw_path, operation=op, content=content, reason=reason)
        )

    return changes


# ---------------------------------------------------------------------------
# CodingAgent
# ---------------------------------------------------------------------------

class CodingAgent:
    """
    Safe Coding Agent.
    Executes exactly one ExecutionStep per invocation using local Ollama + permission-gated tools.
    """

    def __init__(self):
        self._system_prompt = _SYSTEM_PROMPT

    async def process(self, state: AppState) -> AppState:
        # ── Gate 1: execution must be explicitly approved ──────────────────
        if state.get("execution_approval_status") != "APPROVED":
            logger.warning("CodingAgent invoked without explicit execution approval — aborting.")
            return state

        plan = state.get("execution_plan")
        idx = state.get("current_step_index", 0)

        if not plan or idx >= len(plan.ordered_steps):
            return state

        step = plan.ordered_steps[idx]
        session_id = state.get("session_id", "default")
        
        ws = state.get("workspace")
        sandbox_root = Path(ws.root_path) if ws else settings.absolute_workspace_root

        logger.info(
            f"CodingAgent processing step {idx + 1}/{len(plan.ordered_steps)}: '{step.title}'"
        )
        step.status = ExecutionStatus.IN_PROGRESS

        # ── Gate 2: dependency check ────────────────────────────────────────
        if step.dependencies:
            failed_deps = [
                dep_id for dep_id in step.dependencies
                if any(
                    s.id == dep_id and s.status == ExecutionStatus.FAILED
                    for s in plan.ordered_steps
                )
            ]
            if failed_deps:
                reason = f"Step '{step.id}' skipped: dependency step(s) {failed_deps} failed."
                logger.warning(reason)
                step.status = ExecutionStatus.FAILED
                step.result_details = reason
                result = ExecutionResult(step_id=step.id, success=False, error=reason)
                state["execution_results"].append(result)
                return state

        # ── Gate 3: Ollama preflight — before ANY filesystem mutation ───────
        if not await local_llm.is_ollama_online():
            reason = (
                f"Ollama is offline at {local_llm.base_url}. "
                "Cannot generate code. Aborting step to prevent unsafe state."
            )
            logger.error(reason)
            step.status = ExecutionStatus.FAILED
            step.result_details = reason
            result = ExecutionResult(step_id=step.id, success=False, error=reason)
            state["execution_results"].append(result)
            return state

        # ── Gate 4: Checkpoint must already exist before first write ────────
        # The supervisor creates the checkpoint BEFORE calling this agent.
        # If it is missing, refuse to mutate anything.
        if not state.get("git_checkpoint_id"):
            reason = (
                "Git checkpoint is missing. "
                "No file mutations are allowed without a prior checkpoint."
            )
            logger.error(reason)
            step.status = ExecutionStatus.FAILED
            step.result_details = reason
            result = ExecutionResult(step_id=step.id, success=False, error=reason)
            state["execution_results"].append(result)
            return state

        # ── Read existing files for MODIFY context ──────────────────────────
        # We use FSTool for permission-gated reads. FSTool performs its own
        # is_action_permitted(READ_FILE) check — we do NOT duplicate it here.
        fs_tool = FSTool(project_root=sandbox_root, session_id=session_id)
        existing_file_contents: dict = {}

        for file_path in step.files_to_read + step.files_to_modify:
            try:
                content = fs_tool.read_file(file_path)
                existing_file_contents[file_path] = content[:_MAX_EXISTING_FILE_CHARS]
            except PermissionDeniedError:
                # Surface the missing read permission as a pending request.
                # FSTool already called request_permission() internally — just log.
                logger.info(f"Read permission pending for: {file_path}")
                existing_file_contents[file_path] = "<content not yet available — read permission pending>"
            except FileNotFoundError:
                existing_file_contents[file_path] = "<file does not exist yet>"
            except Exception as exc:
                logger.warning(f"Could not read {file_path}: {exc}")
                existing_file_contents[file_path] = f"<read error: {exc}>"

        # ── Build LLM prompt ────────────────────────────────────────────────
        blueprint = state.get("blueprint")
        blueprint_summary = (
            blueprint.objective if blueprint else plan.blueprint_context
        )

        existing_ctx_parts = []
        for fp, fc in existing_file_contents.items():
            existing_ctx_parts.append(f"### Existing file: {fp}\n```\n{fc}\n```")
        existing_ctx = "\n\n".join(existing_ctx_parts) if existing_ctx_parts else "(no existing files to read)"

        prompt = (
            f"PROJECT BLUEPRINT SUMMARY:\n{blueprint_summary}\n\n"
            f"CURRENT EXECUTION STEP:\n"
            f"  ID: {step.id}\n"
            f"  Title: {step.title}\n"
            f"  Description: {step.description}\n"
            f"  Files to modify: {step.files_to_modify}\n"
            f"  Risk level: {step.risk_level}\n\n"
            f"EXISTING FILE CONTENTS:\n{existing_ctx}\n\n"
            f"Generate the file changes required to implement this step. "
            f"Output ONLY a JSON array as specified in your instructions."
        )

        # ── Ollama generation ───────────────────────────────────────────────
        try:
            raw_output = await local_llm.generate(
                prompt=prompt,
                system_prompt=self._system_prompt,
                temperature=0.1,
            )
        except ConnectionError as exc:
            reason = f"Ollama generation failed: {exc}"
            logger.error(reason)
            step.status = ExecutionStatus.FAILED
            step.result_details = reason
            result = ExecutionResult(step_id=step.id, success=False, error=reason)
            state["execution_results"].append(result)
            return state

        # ── Parse + validate LLM output ─────────────────────────────────────
        try:
            file_changes: List[GeneratedFileChange] = _parse_llm_output(raw_output, sandbox_root)
        except ValueError as exc:
            reason = f"Model output validation failed: {exc}"
            logger.error(reason)
            step.status = ExecutionStatus.FAILED
            step.result_details = reason
            result = ExecutionResult(step_id=step.id, success=False, error=reason)
            state["execution_results"].append(result)
            return state

        if not file_changes:
            # Model returned [] — treat as nothing to do for this step (success)
            logger.info(f"Model returned no file changes for step '{step.id}'. Marking complete.")
            step.status = ExecutionStatus.COMPLETED
            step.result_details = "No file changes generated (step may be informational)."
            result = ExecutionResult(
                step_id=step.id,
                success=True,
                output="No file changes generated.",
            )
            state["execution_results"].append(result)
            return state

        # ── Apply file changes via FSTool ───────────────────────────────────
        # IMPORTANT: FSTool.write_file() calls _check_permission(WRITE_FILE) internally.
        # We do NOT call is_action_permitted() here before the tool call.
        # Doing so would consume an ALLOW_ONCE grant, leaving the tool's own check
        # to fail. The tool is the single permission-consuming path.
        written_files: List[str] = []

        for change in file_changes:
            resolved = permission_manager.validate_path(change.path, sandbox_root)

            if change.operation == FileOperation.CREATE:
                # CREATE must not silently overwrite an existing unrelated file.
                if resolved.exists():
                    reason = (
                        f"CREATE refused: file already exists at '{change.path}'. "
                        "Use MODIFY operation to update existing files."
                    )
                    logger.error(reason)
                    step.status = ExecutionStatus.FAILED
                    step.result_details = reason
                    result = ExecutionResult(step_id=step.id, success=False, error=reason)
                    state["execution_results"].append(result)
                    return state

                try:
                    # overwrite=False to be safe (file didn't exist per check above,
                    # but concurrent creation is still guarded)
                    fs_tool.write_file(change.path, change.content, overwrite=False)
                    written_files.append(change.path)
                    logger.info(f"CREATE: {change.path} — {change.reason}")
                except PermissionDeniedError:
                    # FSTool already called request_permission() — surface to user
                    step.status = ExecutionStatus.WAITING_PERMISSION
                    step.result_details = f"Write permission pending for: {change.path}"
                    return state
                except SandboxSecurityError as exc:
                    reason = f"Sandbox violation for CREATE '{change.path}': {exc}"
                    logger.error(reason)
                    step.status = ExecutionStatus.FAILED
                    step.result_details = reason
                    result = ExecutionResult(step_id=step.id, success=False, error=reason)
                    state["execution_results"].append(result)
                    return state

            elif change.operation == FileOperation.MODIFY:
                # MODIFY: file should exist (we read it above). overwrite=True.
                try:
                    fs_tool.write_file(change.path, change.content, overwrite=True)
                    written_files.append(change.path)
                    logger.info(f"MODIFY: {change.path} — {change.reason}")
                except PermissionDeniedError:
                    step.status = ExecutionStatus.WAITING_PERMISSION
                    step.result_details = f"Write permission pending for: {change.path}"
                    return state
                except SandboxSecurityError as exc:
                    reason = f"Sandbox violation for MODIFY '{change.path}': {exc}"
                    logger.error(reason)
                    step.status = ExecutionStatus.FAILED
                    step.result_details = reason
                    result = ExecutionResult(step_id=step.id, success=False, error=reason)
                    state["execution_results"].append(result)
                    return state

        # ── Step complete ────────────────────────────────────────────────────
        output_summary = (
            f"Step '{step.title}' completed. "
            f"Files written: {written_files or 'none'}."
        )
        step.status = ExecutionStatus.COMPLETED
        step.result_details = output_summary

        result = ExecutionResult(
            step_id=step.id,
            success=True,
            output=output_summary,
        )
        state["execution_results"].append(result)
        logger.info(f"CodingAgent completed step '{step.id}': {output_summary}")
        return state


coding_agent = CodingAgent()
