import logging
from typing import Any, Dict, List, Optional

from ..models.schemas import ProjectBlueprint, RequirementQuestion

logger = logging.getLogger("sugio_labs.agents.requirement")


class RequirementAgent:
    """Structured project interview that produces an implementation-ready blueprint."""

    def __init__(self):
        self._standard_questions: List[RequirementQuestion] = [
            RequirementQuestion(
                id="Q1_PROJECT_DOMAIN",
                question="What type of software application are you building?",
                category="general",
                options=[
                    "Student Management System (College ERP / Records)",
                    "E-Commerce & Inventory Management",
                    "Healthcare / Clinic Appointment Booking",
                    "Task Management & Team Collaboration",
                    "Custom Web API & Dashboard",
                ],
                recommended_option="Student Management System (College ERP / Records)",
                recommendation_reason="A strong capstone reference with CRUD, relationships, validation, roles, reporting, and cross-layer contracts.",
            ),
            RequirementQuestion(
                id="Q2_USER_ROLES",
                question="What user roles and permission levels are required?",
                category="auth",
                options=[
                    "Single User (Admin only)",
                    "Multi-Role (Admin, Faculty/Staff, Student)",
                    "Role-Based Access Control (Admin, Manager, Member, Viewer)",
                    "Public Access (No Authentication required)",
                ],
                recommended_option="Multi-Role (Admin, Faculty/Staff, Student)",
                recommendation_reason="Multiple roles create realistic authorization boundaries and contracts to verify.",
            ),
            RequirementQuestion(
                id="Q3_CORE_FEATURES",
                question="What are the key functional features of the application?",
                category="features",
                options=[
                    "Student Profiles, Course Enrollment, Gradebook, Attendance Tracking, Search & Filter",
                    "Product Catalog, Shopping Cart, Order Checkout, Payment Simulation, Inventory Sync",
                    "Doctor Profiles, Patient Appointments, Medical Records, Prescriptions",
                    "Task Board (Kanban), Due Dates, Priority Levels, Activity Timeline",
                ],
                recommended_option="Student Profiles, Course Enrollment, Gradebook, Attendance Tracking, Search & Filter",
                recommendation_reason="Covers CRUD, relationships, validation constraints, filtering, and reporting.",
            ),
            RequirementQuestion(
                id="Q4_FRONTEND_STACK",
                question="What frontend framework and styling system should we use?",
                category="tech_stack",
                options=[
                    "React (TypeScript + Vite + App Workspace UI)",
                    "Next.js (React + TypeScript + App Router)",
                    "Vue.js 3 (Vite + TypeScript)",
                    "Vanilla HTML5 / CSS3 / JavaScript (No framework)",
                ],
                recommended_option="React (TypeScript + Vite + App Workspace UI)",
                recommendation_reason="Fast local builds and strong TypeScript contracts without adding framework overhead.",
            ),
            RequirementQuestion(
                id="Q5_BACKEND_STACK",
                question="What backend framework and architecture do you prefer?",
                category="tech_stack",
                options=[
                    "FastAPI (Python async + Pydantic validation)",
                    "Express.js / Node.js (TypeScript)",
                    "Django REST Framework (Python)",
                    "Flask (Python lightweight)",
                ],
                recommended_option="FastAPI (Python async + Pydantic validation)",
                recommendation_reason="Pydantic request/response models expose clean contracts for automated consistency checks.",
            ),
            RequirementQuestion(
                id="Q6_DATABASE_STACK",
                question="Which database and ORM should handle data persistence?",
                category="database",
                options=[
                    "PostgreSQL (with SQLite fallback for lightweight local dev)",
                    "SQLite (Single-file zero-configuration database)",
                    "MongoDB / Document Database",
                    "MySQL / MariaDB",
                ],
                recommended_option="PostgreSQL (with SQLite fallback for lightweight local dev)",
                recommendation_reason="Relational integrity for production-style data with a zero-friction SQLite local option.",
            ),
            RequirementQuestion(
                id="Q7_TESTING_STRATEGY",
                question="What verification and automated testing strategy should be applied?",
                category="testing",
                options=[
                    "Pytest (Backend API + Unit) & Vitest (Frontend Components) + Contract Graph Validation",
                    "Pytest Backend API testing only",
                    "Basic manual verification and health checks",
                ],
                recommended_option="Pytest (Backend API + Unit) & Vitest (Frontend Components) + Contract Graph Validation",
                recommendation_reason="Catches regressions at the API, component, and cross-layer contract levels.",
            ),
        ]

    def get_question(self, index: int) -> Optional[RequirementQuestion]:
        return self._standard_questions[index] if 0 <= index < len(self._standard_questions) else None

    def get_all_questions(self) -> List[RequirementQuestion]:
        return self._standard_questions

    @staticmethod
    def _roles(value: str) -> List[str]:
        cleaned = value
        for prefix in ["Multi-Role (", "Role-Based Access Control ("]:
            cleaned = cleaned.replace(prefix, "")
        cleaned = cleaned.replace(")", "")
        if value.startswith("Single User"):
            return ["Admin"]
        if value.startswith("Public Access"):
            return ["Public"]
        return [part.strip() for part in cleaned.split(",") if part.strip()]

    @staticmethod
    def _domain_preset(domain: str) -> Dict[str, Any]:
        lowered = domain.lower()
        if "e-commerce" in lowered:
            return {
                "project_name": "E-Commerce & Inventory Management",
                "entity": "Product",
                "plural": "products",
                "table": "products",
                "fields": [
                    "id INTEGER PRIMARY KEY",
                    "sku VARCHAR(64) UNIQUE NOT NULL",
                    "name VARCHAR(255) NOT NULL",
                    "price DECIMAL(10,2) NOT NULL",
                    "stock INTEGER NOT NULL DEFAULT 0",
                    "status VARCHAR(30) NOT NULL",
                    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                ],
                "secondary_table": {
                    "table": "orders",
                    "columns": [
                        "id INTEGER PRIMARY KEY",
                        "customer_email VARCHAR(255) NOT NULL",
                        "total DECIMAL(10,2) NOT NULL",
                        "status VARCHAR(30) NOT NULL",
                        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    ],
                },
            }
        if "healthcare" in lowered or "clinic" in lowered:
            return {
                "project_name": "Clinic Appointment & Records",
                "entity": "Patient",
                "plural": "patients",
                "table": "patients",
                "fields": [
                    "id INTEGER PRIMARY KEY",
                    "name VARCHAR(255) NOT NULL",
                    "email VARCHAR(255) UNIQUE",
                    "phone VARCHAR(30)",
                    "date_of_birth DATE",
                    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                ],
                "secondary_table": {
                    "table": "appointments",
                    "columns": [
                        "id INTEGER PRIMARY KEY",
                        "patient_id INTEGER REFERENCES patients(id)",
                        "doctor_name VARCHAR(255) NOT NULL",
                        "scheduled_at TIMESTAMP NOT NULL",
                        "status VARCHAR(30) NOT NULL",
                    ],
                },
            }
        if "task" in lowered or "collaboration" in lowered:
            return {
                "project_name": "Task Management & Team Collaboration",
                "entity": "Task",
                "plural": "tasks",
                "table": "tasks",
                "fields": [
                    "id INTEGER PRIMARY KEY",
                    "title VARCHAR(255) NOT NULL",
                    "description TEXT",
                    "status VARCHAR(30) NOT NULL",
                    "priority VARCHAR(20) NOT NULL",
                    "due_date DATE",
                    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                ],
                "secondary_table": {
                    "table": "task_activity",
                    "columns": [
                        "id INTEGER PRIMARY KEY",
                        "task_id INTEGER REFERENCES tasks(id)",
                        "event_type VARCHAR(50) NOT NULL",
                        "message TEXT NOT NULL",
                        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    ],
                },
            }
        if "custom" in lowered:
            return {
                "project_name": "Custom Web API & Dashboard",
                "entity": "Record",
                "plural": "records",
                "table": "records",
                "fields": [
                    "id INTEGER PRIMARY KEY",
                    "name VARCHAR(255) NOT NULL",
                    "status VARCHAR(30) NOT NULL",
                    "metadata JSON",
                    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                ],
                "secondary_table": None,
            }
        return {
            "project_name": "Student Management System",
            "entity": "Student",
            "plural": "students",
            "table": "students",
            "fields": [
                "id INTEGER PRIMARY KEY",
                "roll_number VARCHAR(50) UNIQUE NOT NULL",
                "name VARCHAR(255) NOT NULL",
                "email VARCHAR(255) UNIQUE NOT NULL",
                "course VARCHAR(100) NOT NULL",
                "phone VARCHAR(20)",
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            ],
            "secondary_table": {
                "table": "courses",
                "columns": [
                    "id INTEGER PRIMARY KEY",
                    "code VARCHAR(20) UNIQUE NOT NULL",
                    "title VARCHAR(255) NOT NULL",
                    "credits INTEGER NOT NULL",
                ],
            },
        }

    def generate_blueprint_from_answers(self, answers: Dict[str, str]) -> ProjectBlueprint:
        domain = answers.get("Q1_PROJECT_DOMAIN", "Student Management System (College ERP / Records)")
        roles_value = answers.get("Q2_USER_ROLES", "Multi-Role (Admin, Faculty/Staff, Student)")
        features_value = answers.get("Q3_CORE_FEATURES", "Student Profiles, Course Enrollment, Gradebook, Attendance Tracking")
        frontend = answers.get("Q4_FRONTEND_STACK", "React (TypeScript + Vite + App Workspace UI)")
        backend = answers.get("Q5_BACKEND_STACK", "FastAPI (Python async + Pydantic validation)")
        database = answers.get("Q6_DATABASE_STACK", "PostgreSQL (with SQLite fallback for lightweight local dev)")
        testing = answers.get("Q7_TESTING_STRATEGY", "Pytest + Vitest + Contract Graph Validation")

        preset = self._domain_preset(domain)
        entity = preset["entity"]
        plural = preset["plural"]
        roles = self._roles(roles_value)
        features = [feature.strip() for feature in features_value.split(",") if feature.strip()]

        frontend_modules = [
            {"name": f"{entity}List", "path": f"src/features/{plural}/{entity}List.tsx", "purpose": f"Browse, filter, and manage {plural}"},
            {"name": f"{entity}Form", "path": f"src/features/{plural}/{entity}Form.tsx", "purpose": f"Create and edit {entity.lower()} data with validation"},
            {"name": "Dashboard", "path": "src/features/dashboard/Dashboard.tsx", "purpose": "Operational summary and navigation"},
        ]
        backend_modules = [
            {"name": f"{entity}Router", "path": f"app/api/{plural}.py", "purpose": f"REST endpoints for {entity.lower()} operations"},
            {"name": f"{entity}Service", "path": f"app/services/{plural}.py", "purpose": "Business rules and transaction orchestration"},
            {"name": f"{entity}Model", "path": f"app/models/{plural}.py", "purpose": "Persistence model"},
            {"name": f"{entity}Schemas", "path": f"app/schemas/{plural}.py", "purpose": "Request and response validation contracts"},
        ]
        api_endpoints = [
            {"method": "GET", "path": f"/api/v1/{plural}", "description": f"List {plural} with filters and pagination"},
            {"method": "POST", "path": f"/api/v1/{plural}", "description": f"Create a new {entity.lower()}"},
            {"method": "GET", "path": f"/api/v1/{plural}/{{id}}", "description": f"Get one {entity.lower()}"},
            {"method": "PUT", "path": f"/api/v1/{plural}/{{id}}", "description": f"Update a {entity.lower()}"},
            {"method": "DELETE", "path": f"/api/v1/{plural}/{{id}}", "description": f"Delete a {entity.lower()}"},
        ]
        db_schema = [{"table": preset["table"], "columns": preset["fields"]}]
        if preset.get("secondary_table"):
            db_schema.append(preset["secondary_table"])

        return ProjectBlueprint(
            project_name=preset["project_name"],
            objective=f"Build a local-first {domain} with consistent contracts, explicit permissions, and automated verification.",
            user_roles=roles,
            features=features,
            functional_requirements=[
                f"FR-1: Enforce access rules for {', '.join(roles)}.",
                f"FR-2: Provide validated CRUD workflows for {plural}.",
                "FR-3: Support useful search, filtering, and operational feedback.",
                "FR-4: Keep frontend payloads, API schemas, services, persistence, and tests synchronized.",
                "FR-5: Record agent activity and require approval for risky mutations.",
            ],
            non_functional_requirements=[
                "NFR-1: Run fully on the local development machine by default.",
                "NFR-2: Keep source code and project data local unless the user explicitly connects an external tool.",
                "NFR-3: Gate file writes, shell execution, migrations, and destructive Git operations.",
                "NFR-4: Provide a responsive developer-workspace UI with clear system and contract state.",
            ],
            selected_stack={
                "frontend": frontend,
                "backend": backend,
                "database": database,
                "testing": testing,
                "agent_core": "LangGraph + Ollama/fallback + NetworkX Contract Graph",
            },
            architecture_summary=(
                "A typed frontend talks to versioned API routes. Backend services own business rules and persistence. "
                "The Contract Graph maps dependencies across requirements, UI, API, services, database, and tests; "
                "the permission gateway sits in front of mutation-capable tools."
            ),
            frontend_modules=frontend_modules,
            backend_modules=backend_modules,
            api_endpoints=api_endpoints,
            db_schema=db_schema,
            folder_structure=[
                "frontend/src/features/",
                "frontend/src/services/",
                "frontend/src/types/",
                "backend/app/api/",
                "backend/app/services/",
                "backend/app/models/",
                "backend/app/schemas/",
                "backend/tests/",
            ],
            testing_strategy=testing,
            development_steps=[
                "1. Create persistence models and request/response schemas.",
                "2. Implement services and API routes with validation.",
                "3. Build typed frontend workflows against the API contracts.",
                "4. Generate Contract Graph nodes and dependency edges.",
                "5. Run automated tests and contract drift verification before applying changes.",
            ],
            risks=[
                "Cross-layer schema drift when fields or routes change independently.",
                "Destructive local mutations without an explicit checkpoint and permission decision.",
                "Local model availability or hardware constraints; mitigated by deterministic fallback behavior.",
            ],
            approved=False,
        )


requirement_agent = RequirementAgent()
