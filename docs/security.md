# Sugio Labs — Security & Permission Architecture

## 1. Zero-Trust Local Execution
The agent operates under a strict Zero-Trust principle:
- **No Unrestricted Execution**: The LLM cannot directly call `subprocess.run` or arbitrary shell scripts without passing through the Permission Gateway.
- **Project Sandbox Containment**: All file operations (`read`, `write`, `delete`, `mkdir`) are validated against the approved `project_root` canonical path. Attempts to traverse directories outside the sandbox (`../..`) are blocked.
- **Three-Tier Permission State**:
  - `Allow Once`: Approved for the single execution lifecycle.
  - `Allow for This Project`: Remembered for the duration of the active project session.
  - `Reject`: Action is cancelled; supervisor is informed to plan an alternative or prompt the user.

## 2. Privacy & Offline Safety
- Source code remains exclusively on the local host.
- Local LLMs (Ollama) are prioritized.
- External internet access requires explicit user confirmation.
