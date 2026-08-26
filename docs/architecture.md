# Sugio Labs — Architecture Guide

## 1. High-Level Design

Sugio Labs is structured as a decoupled client-server agentic system:

1. **Frontend (React + TypeScript + Vite)**: Provides a dark-mode, responsive web UI for developer interaction, multi-phase interview wizard, real-time activity timelines, interactive Contract Graph visualization, and multilingual audio/visual feedback.
2. **Backend API (FastAPI + WebSockets)**: Manages sessions, REST API endpoints, real-time message broadcasting, and agent orchestration.
3. **Agent Core (LangGraph + Ollama)**: An orchestrator/supervisor running specialized sub-agent routines (Requirement, Architecture, Contract Graph, Impact Analyzer, Coding, Testing).
4. **Contract Graph Engine (NetworkX)**: An in-memory and persistent graph mapping connections between Requirements, Frontend Components, API Endpoints, Backend Handlers, Database Schemas, Validation Rules, and Tests.
5. **Security & Permission Manager**: Intercepts any proposed filesystem, terminal, or MCP tool execution, enforcing `Allow Once`, `Allow for This Project`, or `Reject`.

---

## 2. Agent Execution Flow

```text
1. Requirement Interview ➔ Structured Spec + Blueprint (User Approval Required)
2. Blueprint to Contract Graph ➔ Node & Dependency Generation
3. Code Generation ➔ Frontend + API + Backend + Database + Tests
4. Change Request ➔ Impact Analyzer ➔ Risk & Cross-Layer Diff Presentation
5. Tool Execution ➔ Permission Gateway ➔ User Approval ➔ MCP Tool Execution
6. Verification ➔ Build + Tests + Contract Consistency Check ➔ Pass / Suggest Fix / Rollback
```
