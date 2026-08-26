# Sugio Labs — Contract Graph Specification

## 1. What is the Contract Graph?

The **Contract Graph** is Sugio Labs' core differentiator. It builds a directed acyclic graph (DAG) representing the semantic dependencies between all software layers:

```text
[Requirement Node]
       │
       ▼
[Frontend Component Node]
       │ (sends payload / invokes)
       ▼
[API Endpoint Node]
       │ (routes to)
       ▼
[Backend Handler / Service Node]
       │ (persists / queries)
       ▼
[Database Table & Field Node]
       │ (validated by)
       ▼
[Validation Rule & Test Suite Node]
```

## 2. Node Schema
- `id`: Unique string identifier (e.g. `req:student_phone`, `fe:StudentForm.tsx`, `api:post_students`, `db:students.phone`)
- `type`: `requirement` | `frontend` | `api` | `backend` | `database` | `test`
- `name`: Human-readable label
- `layer`: Target application tier
- `metadata`: JSON payload containing field names, HTTP methods, SQL column types, test assertions
- `status`: `synchronized` | `modified` | `violated` | `pending_approval`

## 3. Impact Detection & Violation Rules
When a field is renamed or added (e.g. `phone` in Frontend vs `phone_number` in Backend):
1. The engine checks connected edge signatures.
2. If field names or types mismatch between adjacent layer nodes, a `CrossLayerContractViolation` is emitted.
3. The Impact Analyzer maps all ancestor and descendant nodes to show the blast radius.
