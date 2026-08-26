import pytest
from app.agents.supervisor import AgentSupervisor
from app.models.schemas import PermissionResponse, PermissionDecision


@pytest.mark.asyncio
async def test_supervisor_interview_flow():
    supervisor = AgentSupervisor()

    # Start interview
    first_q = await supervisor.start_interview()
    assert first_q.id == "Q1_PROJECT_DOMAIN"

    # Answer all questions
    questions = [
        ("Q1_PROJECT_DOMAIN", "Student Management System (College ERP / Records)"),
        ("Q2_USER_ROLES", "Multi-Role (Admin, Faculty/Staff, Student)"),
        ("Q3_CORE_FEATURES", "Student Profiles, Course Enrollment, Gradebook, Attendance Tracking"),
        ("Q4_FRONTEND_STACK", "React (TypeScript + Vite + Glassmorphic Dark Mode)"),
        ("Q5_BACKEND_STACK", "FastAPI (Python async + Pydantic validation)"),
        ("Q6_DATABASE_STACK", "PostgreSQL (with SQLite fallback)"),
        ("Q7_TESTING_STRATEGY", "Pytest & Vitest + Contract Graph Validation"),
    ]

    last_res = None
    for q_id, ans in questions:
        last_res = await supervisor.answer_question(q_id, ans)

    assert last_res["status"] == "blueprint_ready"
    blueprint = last_res["blueprint"]
    assert blueprint["project_name"] == "Student Management System"

    # Approve blueprint
    approved_res = await supervisor.approve_blueprint()
    assert approved_res["status"] == "success"
    assert approved_res["blueprint"]["approved"] is True


@pytest.mark.asyncio
async def test_supervisor_change_request_and_permission():
    supervisor = AgentSupervisor()
    await supervisor.start_interview()

    # Handle change request
    change_res = await supervisor.handle_change_request("Add emergency contact phone number to student profile")
    assert "impact_report" in change_res
    assert "permission_request" in change_res

    perm_id = change_res["permission_request"]["id"]

    # Submit user approval
    decision = PermissionResponse(
        request_id=perm_id,
        decision=PermissionDecision.ALLOW_ONCE,
    )
    perm_res = await supervisor.submit_permission_decision(decision)
    assert perm_res["granted"] is True
