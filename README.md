# Sugio Labs 🚀

> **Local, Human-Controlled AI Software Development Agent**  
> Ensuring Cross-Layer Software Consistency (`Frontend ↔ Backend ↔ API ↔ Database ↔ Tests`) through a Contract Graph.

---

## 🌟 Overview

**Sugio Labs** is a local-first software development agent that assists engineering teams in building and evolving full-stack applications. Unlike generic code generators, Sugio Labs focuses on **architectural consistency, human governance, and safety**:

1. **Human-in-the-Loop Governance**: Every critical file mutation, shell command, or MCP tool execution is gated behind explicit user permissions (`Allow Once`, `Allow for This Project`, `Reject`).
2. **Contract Graph Engine**: Tracks dependencies across requirements, frontend components, API endpoints, backend services, database schemas, validation rules, and automated tests.
3. **Cross-Layer Impact Analyzer**: Predicts and highlights ripple effects, schema drifts, and contract violations before any code is modified.
4. **Local-First & Private**: Powered by local LLMs (via Ollama) with zero code sent to cloud APIs.
5. **Git Safety & Checkpoints**: Automatic rollback checkpoints before applying multi-file mutations.
6. **Multilingual Interaction**: Voice and text communication in English, Tamil, and Tanglish.

---

## 👥 2-Member Team Roles

| Member | Role | Core Ownership |
| :--- | :--- | :--- |
| **Member 1** | **AI / Backend Lead** | FastAPI Backend, LangGraph Supervisor, Ollama Integration, Contract Graph Engine (NetworkX), Impact Analyzer, Permission Gateway, MCP Tools |
| **Member 2** | **Frontend / Integration Lead** | React + TS Dashboard, Requirement Interview UI, Approval Dialogs, Graph Visualization, WebSockets, Voice Engine (EN/TA/Tanglish), E2E Testing |

---

## 🏗️ Architecture

```text
User ↔ React Dashboard ↔ FastAPI (REST + WebSockets) ↔ LangGraph Supervisor
                                                            │
                 ┌──────────────────────────────────────────┴────────────────────────┐
                 ▼                                                                   ▼
    Requirement & Architecture Agents                                   Contract Graph & Impact Engine
                 │                                                                   │
                 └──────────────────────────────────┬────────────────────────────────┘
                                                    ▼
                                            Permission Gateway
                                        [Allow Once | Project | Reject]
                                                    │
                                                    ▼
                                            MCP Client Layer
                                 (Filesystem, Terminal, Git, DB, Docs)
                                                    │
                                                    ▼
                                            Local Project Workspace
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.11+** with `uv` package manager (`curl -LsSf https://astral.sh/uv/install.ps1 | iex` on Windows)
- **Node.js 18+** & `npm`
- **Git**
- **Ollama** (optional, with fallback to built-in local heuristic engine)

### 2. Backend Setup
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit the dashboard at `http://localhost:5173`.

---

## 🧪 Running Tests
```bash
cd backend
uv run pytest -v
```

---

## 📜 License
MIT License - Created for Sugio Labs College Capstone Project.
