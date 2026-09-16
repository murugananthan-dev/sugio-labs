# Sugio Labs

**Local, human-controlled AI software development workspace** that keeps frontend, API, backend, database, and test contracts synchronized before code changes spread across the stack.

Sugio Labs is designed as a developer app rather than a generic chatbot. The workspace combines project planning, architecture blueprints, a Contract Graph, impact analysis, explicit permission gates, Git safety checkpoints, live agent activity, and local AI assistance.

## What works in the rebuilt app

- **Project planning interview** with stack, role, feature, database, and verification decisions.
- **Domain-aware blueprints** for student systems, commerce/inventory, clinic workflows, task collaboration, and custom dashboards.
- **Project-specific Contract Graphs** generated from the approved blueprint instead of a fixed demo graph.
- **Cross-layer impact analysis** using the entity, route, component, or field you actually enter.
- **Human-in-the-loop approvals** for risky file, shell, Git, and tool operations.
- **Git checkpoints and rollback** inside the local project sandbox.
- **Local assistant** using Ollama when available, with a deterministic offline fallback when Ollama is not running.
- **Live WebSocket activity** with REST fallback for the main application flows.
- **Responsive developer-workspace UI** with desktop, tablet, and mobile layouts.

## Architecture

```text
React + TypeScript workspace
        │
        ├── REST ───────────────┐
        └── WebSocket events ───┤
                               ▼
                         FastAPI backend
                               │
                    LangGraph supervisor
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
     Requirement agent   Contract Graph    Permission gateway
             │             (NetworkX)             │
             └─────────────────┬───────────────────┘
                               ▼
                     Local tools / workspace
                   Filesystem · Shell · Git · MCP
                               │
                               ▼
                       Local project sandbox

Local AI: Ollama when available → deterministic local fallback otherwise
```

## Requirements

- Python **3.11+**
- [`uv`](https://docs.astral.sh/uv/)
- Node.js **18+** (Node 20 recommended)
- npm
- Git
- Ollama is optional. The app remains usable without it.

## Install

### Backend

```bash
cd backend
uv sync --extra dev
```

### Frontend

```bash
cd frontend
npm ci
```

## Run the complete app

From the repository root:

```bash
python dev.py
```

Then open:

- App: `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8000`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

You can also run the services separately:

```bash
# terminal 1
cd backend
uv run uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
npm run dev
```

## Optional Ollama setup

Start Ollama locally and install a coding-capable model, for example:

```bash
ollama pull qwen2.5-coder:7b
ollama serve
```

Set the model in `backend/.env` if you want something other than the configured default. If Ollama is unavailable, the assistant automatically uses Sugio's built-in local fallback for architecture, contract, verification, and safety guidance.

## Tests and verification

Backend tests:

```bash
cd backend
uv run pytest -v
```

Frontend production build:

```bash
cd frontend
npm run build
```

GitHub CI runs both checks for pull requests and for the rebuild branch.

## Core workflow

1. **Plan** — answer the structured project interview.
2. **Blueprint** — review modules, routes, stack, and persistence decisions.
3. **Approve** — generate a project-specific cross-layer Contract Graph.
4. **Impact** — describe a requested change and inspect its blast radius.
5. **Permission** — explicitly allow or reject risky mutations.
6. **Checkpoint** — create restore points around multi-file work.
7. **Verify** — run backend tests, frontend builds, and contract checks.

## Project structure

```text
backend/
  app/
    agents/          # planning, supervisor, local AI
    api/             # REST + WebSocket surface
    contract_graph/  # dependency and impact engine
    permissions/     # human approval gateway
    tools/           # filesystem, shell, Git, MCP
  tests/

frontend/
  src/
    App.tsx          # main developer workspace
    services/        # REST and WebSocket clients
    types/           # shared frontend contracts
    index.css        # app design system

dev.py               # starts backend + frontend together
```

## Safety model

Sugio Labs is intentionally human-controlled. Operations with side effects are routed through the permission gateway. Project-level approval is available for trusted repeated actions, while unfamiliar or destructive work can stay on one-time approval.

Git checkpoints complement the permission system by making multi-file changes easier to recover from when verification fails.

## License

MIT — created as the Sugio Labs college capstone project.
