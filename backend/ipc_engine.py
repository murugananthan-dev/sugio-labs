"""Sugio Labs native desktop Python backend.

The WPF desktop app launches this process and communicates over newline-delimited
JSON on stdin/stdout. No HTTP server, browser, WebSocket, or web runtime is
required by the shipped desktop software.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import traceback
from typing import Any

from app.agents.base import local_llm
from app.agents.requirement_agent import requirement_agent
from app.agents.supervisor import agent_supervisor, chat_graph
from app.contract_graph.graph import contract_graph
from app.models.schemas import PermissionResponse
from app.permissions.manager import PermissionDeniedError
from app.tools.git_tools import GitTool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("sugio_labs.ipc")

git_tool = GitTool()


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


async def handle_command(command: str, payload: dict[str, Any]) -> Any:
    if command == "ping":
        return {"status": "ok", "service": "Sugio Labs Python Engine", "transport": "stdio-json"}

    if command == "health":
        ollama_ok = await local_llm.is_ollama_online()
        models = await local_llm.list_local_models() if ollama_ok else []
        return {
            "status": "healthy",
            "backend": "python",
            "ollama_online": ollama_ok,
            "models": models,
            "assistant_mode": "ollama" if ollama_ok else "local_fallback",
            "hardware": local_llm.get_hardware_profile(),
        }

    if command == "interview_questions":
        return _jsonable(requirement_agent.get_all_questions())

    if command == "interview_start":
        return {"question": _jsonable(await agent_supervisor.start_interview())}

    if command == "interview_answer":
        return await agent_supervisor.answer_question(
            str(payload.get("question_id", "")),
            str(payload.get("answer", "")),
        )

    if command == "blueprint_approve":
        return await agent_supervisor.approve_blueprint()

    if command == "contract_graph":
        return _jsonable(contract_graph.export_graph())

    if command == "impact_analysis":
        return await agent_supervisor.handle_change_request(
            change_description=str(payload.get("change_description", "")),
            target_entity=str(payload.get("target_entity", "")),
        )

    if command == "permission_decision":
        response = PermissionResponse.model_validate(payload)
        return await agent_supervisor.submit_permission_decision(response)

    if command == "session_state":
        state = agent_supervisor.get_session_state()
        state["activity_logs"] = [item.model_dump(mode="json") for item in agent_supervisor.activity_logs]
        state["checkpoints"] = [_jsonable(item) for item in git_tool.list_checkpoints()]
        return state

    if command == "checkpoint_list":
        return [_jsonable(item) for item in git_tool.list_checkpoints()]

    if command == "checkpoint_create":
        checkpoint = git_tool.create_checkpoint(
            str(payload.get("name", "Checkpoint")),
            str(payload.get("description", "")),
        )
        return {"status": "created", "checkpoint": _jsonable(checkpoint)}

    if command == "git_diff":
        return {"diff": git_tool.get_diff()}

    if command == "git_rollback":
        checkpoint_id = str(payload.get("checkpoint_id", ""))
        try:
            git_tool.rollback_to_checkpoint(checkpoint_id)
            return {"status": "success", "rolled_back_to": checkpoint_id}
        except PermissionDeniedError as exc:
            return {
                "status": "permission_required",
                "message": str(exc),
                "checkpoint_id": checkpoint_id,
            }

    if command == "chat":
        language = str(payload.get("language", "en"))
        message = str(payload.get("message", ""))
        result = chat_graph.invoke(
            {
                "messages": [{"role": "user", "content": message}],
                "language": language,
            }
        )
        reply = result["messages"][-1]["content"] if result.get("messages") else "No response generated."
        return {"reply": reply, "language": language}

    if command == "shutdown":
        return {"status": "bye", "shutdown": True}

    raise ValueError(f"Unknown command: {command}")


async def process_request(request: dict[str, Any]) -> dict[str, Any]:
    request_id = str(request.get("id", ""))
    command = str(request.get("command", ""))
    payload = request.get("payload") or {}

    try:
        result = await handle_command(command, payload)
        return {"id": request_id, "ok": True, "result": _jsonable(result)}
    except Exception as exc:
        logger.error("IPC command %s failed: %s\n%s", command, exc, traceback.format_exc())
        return {
            "id": request_id,
            "ok": False,
            "error": {
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        }


def main() -> int:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {
                "id": "",
                "ok": False,
                "error": {"type": "JSONDecodeError", "message": str(exc)},
            }
        else:
            response = asyncio.run(process_request(request))

        sys.stdout.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
        sys.stdout.flush()

        if response.get("ok") and response.get("result", {}).get("shutdown"):
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
