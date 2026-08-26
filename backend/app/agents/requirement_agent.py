import logging
from typing import List, Dict, Any, Optional
from ..models.schemas import (
    RequirementQuestion,
    RequirementSpec,
    ProjectBlueprint,
)

logger = logging.getLogger("sugio_labs.agents.requirement")


class RequirementAgent:
    """
    Requirement Gathering Interview Agent.
    Asks structured, one-by-one questions with intelligent recommendations and produces a complete Project Blueprint.
    """

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
                recommendation_reason="Ideal reference application for comprehensive cross-layer contract verification and college project demonstration.",
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
                recommendation_reason="Provides distinct data contracts, authentication boundaries, and permission models across application tiers.",
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
                recommendation_reason="Comprehensive feature set covering CRUD, relationships, validation constraints, and search queries.",
            ),
            RequirementQuestion(
                id="Q4_FRONTEND_STACK",
                question="What frontend framework and styling system should we use?",
                category="tech_stack",
                options=[
                    "React (TypeScript + Vite + Glassmorphic Dark Mode)",
                    "Next.js (React + TypeScript + App Router)",
                    "Vue.js 3 (Vite + TypeScript)",
                    "Vanilla HTML5 / CSS3 / JavaScript (No framework)",
                ],
                recommended_option="React (TypeScript + Vite + Glassmorphic Dark Mode)",
                recommendation_reason="Fastest local dev build with Vite, strong TypeScript typing for Contract Graph alignment, and stunning modern aesthetics.",
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
                recommendation_reason="Native Pydantic schema validation enables automated cross-layer contract synchronization with zero boilerplate.",
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
                recommendation_reason="Standard relational integrity, foreign key cascades, and easy offline local development with SQLite fallback.",
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
                recommendation_reason="Ensures end-to-end regression prevention and validates consistency between all 5 layers.",
            ),
        ]

    def get_question(self, index: int) -> Optional[RequirementQuestion]:
        """Gets a question by its 0-based index."""
        if 0 <= index < len(self._standard_questions):
            return self._standard_questions[index]
        return None

    def get_all_questions(self) -> List[RequirementQuestion]:
        """Returns the full list of interview questions."""
        return self._standard_questions

    def generate_blueprint_from_answers(
        self,
        answers: Dict[str, str],
        project_name: str = "Student Management System",
    ) -> ProjectBlueprint:
        """
        Synthesizes collected answers into a comprehensive, structured Project Blueprint.
        """
        domain = answers.get("Q1_PROJECT_DOMAIN", "Student Management System")
        roles_str = answers.get("Q2_USER_ROLES", "Admin, Faculty, Student")
        features_str = answers.get("Q3_CORE_FEATURES", "Student Profiles, Course Enrollment, Gradebook, Attendance")
        frontend = answers.get("Q4_FRONTEND_STACK", "React (TypeScript + Vite)")
        backend = answers.get("Q5_BACKEND_STACK", "FastAPI (Python)")
        database = answers.get("Q6_DATABASE_STACK", "PostgreSQL / SQLite")
        testing = answers.get("Q7_TESTING_STRATEGY", "Pytest + Vitest + Contract Graph")

        roles = [r.strip() for r in roles_str.replace("Multi-Role (", "").replace(")", "").split(",")]
        features = [f.strip() for f in features_str.split(",")]

        return ProjectBlueprint(
            project_name=project_name,
            objective=f"Develop a high-performance {domain} featuring full cross-layer contract consistency, role-based access, and automated verification.",
            user_roles=roles,
            features=features,
            functional_requirements=[
                f"FR-1: User authentication and role enforcement for {', '.join(roles)}.",
                "FR-2: Complete CRUD operations on student profiles, course registrations, and attendance.",
                "FR-3: Real-time search, sorting, and pagination across records.",
                "FR-4: Data validation on phone numbers, email formats, and unique roll numbers.",
                "FR-5: Export and reporting capabilities in CSV/JSON formats.",
            ],
            non_functional_requirements=[
                "NFR-1: Sub-100ms API response time on local queries.",
                "NFR-2: Zero cloud telemetry — all source code and database records remain strictly local.",
                "NFR-3: Zero-trust permission gateway on all file writes and migrations.",
                "NFR-4: Modern dark-mode responsive glassmorphic UI with accessibility.",
            ],
            selected_stack={
                "frontend": frontend,
                "backend": backend,
                "database": database,
                "testing": testing,
                "agent_core": "LangGraph + Ollama + NetworkX Contract Graph",
            },
            architecture_summary="3-tier decoupled architecture: React Single-Page Application communicating via REST/WebSockets to FastAPI services, backed by relational ORM with automatic Contract Graph verification.",
            frontend_modules=[
                {"name": "StudentList", "path": "src/components/StudentList.tsx", "purpose": "Display, filter, and paginate student records"},
                {"name": "StudentForm", "path": "src/components/StudentForm.tsx", "purpose": "Create and edit student details with form validation"},
                {"name": "CourseEnrollment", "path": "src/components/CourseEnrollment.tsx", "purpose": "Enroll students into courses and manage electives"},
                {"name": "AttendanceTracker", "path": "src/components/AttendanceTracker.tsx", "purpose": "Mark daily attendance and compute percentages"},
            ],
            backend_modules=[
                {"name": "StudentRouter", "path": "app/api/students.py", "purpose": "REST endpoints for student CRUD"},
                {"name": "StudentService", "path": "app/services/student_service.py", "purpose": "Business logic and transaction management"},
                {"name": "StudentModel", "path": "app/models/student.py", "purpose": "SQLAlchemy ORM schema for student entity"},
                {"name": "StudentSchemas", "path": "app/schemas/student.py", "purpose": "Pydantic request/response validation schemas"},
            ],
            api_endpoints=[
                {"method": "GET", "path": "/api/v1/students", "description": "List all students with query filters"},
                {"method": "POST", "path": "/api/v1/students", "description": "Create new student profile"},
                {"method": "GET", "path": "/api/v1/students/{id}", "description": "Retrieve specific student details"},
                {"method": "PUT", "path": "/api/v1/students/{id}", "description": "Update student information"},
                {"method": "DELETE", "path": "/api/v1/students/{id}", "description": "Delete student record"},
                {"method": "POST", "path": "/api/v1/students/{id}/enroll", "description": "Enroll student into course"},
            ],
            db_schema=[
                {
                    "table": "students",
                    "columns": [
                        "id INTEGER PRIMARY KEY",
                        "roll_number VARCHAR(50) UNIQUE NOT NULL",
                        "name VARCHAR(255) NOT NULL",
                        "email VARCHAR(255) UNIQUE NOT NULL",
                        "course VARCHAR(100) NOT NULL",
                        "phone VARCHAR(20)",
                        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    ],
                },
                {
                    "table": "courses",
                    "columns": [
                        "id INTEGER PRIMARY KEY",
                        "code VARCHAR(20) UNIQUE NOT NULL",
                        "title VARCHAR(255) NOT NULL",
                        "credits INTEGER NOT NULL",
                    ],
                },
                {
                    "table": "enrollments",
                    "columns": [
                        "id INTEGER PRIMARY KEY",
                        "student_id INTEGER REFERENCES students(id)",
                        "course_id INTEGER REFERENCES courses(id)",
                        "grade VARCHAR(5)",
                        "enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    ],
                },
            ],
            folder_structure=[
                "frontend/src/components/",
                "frontend/src/services/",
                "frontend/src/types/",
                "backend/app/api/",
                "backend/app/models/",
                "backend/app/services/",
                "backend/tests/",
            ],
            testing_strategy="Automated Pytest API test suite verifying status codes, schema payloads, and database rollback, paired with Vitest component snapshot testing.",
            development_steps=[
                "1. Initialize database schema and migrations.",
                "2. Implement backend Pydantic schemas and FastAPI route handlers.",
                "3. Build React UI components with responsive glassmorphic cards.",
                "4. Construct Contract Graph nodes and register cross-layer edge dependencies.",
                "5. Execute automated test suite and verify contract integrity.",
            ],
            risks=[
                "Schema drift if frontend form fields do not match backend Pydantic models (Mitigated by Contract Graph).",
                "Unauthorized filesystem mutations (Mitigated by Zero-Trust Permission Gateway).",
            ],
            approved=False,
        )


requirement_agent = RequirementAgent()
