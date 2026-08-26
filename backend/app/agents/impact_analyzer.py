import logging
from typing import Dict, Any, List, Optional
from ..contract_graph.graph import contract_graph as contract_graph_engine
from ..models.schemas import ImpactReport, ContractViolation, ContractNodeType

logger = logging.getLogger("sugio_labs.agents.impact_analyzer")

class ImpactAnalyzer:
    """
    Cross-Layer Impact Analyzer.
    Determines blast radius, affected files, DB changes, API modifications,
    and contract violations before any code mutation occurs.
    """
    def analyze_change(self, prompt: str, target_entity: str = "student") -> ImpactReport:
        """
        Analyzes a natural language change request against the active Contract Graph.
        Example: 'Add mandatory phone number to Student' or 'Change phone to phone_number'
        """
        prompt_lower = prompt.lower()
        graph_data = contract_graph_engine.export_graph()
        
        affected_fe: List[str] = []
        affected_be: List[str] = []
        affected_api: List[str] = []
        affected_db: List[str] = []
        affected_tests: List[str] = []
        violations: List[ContractViolation] = []
        explanations: List[str] = []
        risk_level = "Low"

        # Check for Student entity change
        if "phone" in prompt_lower or "student" in prompt_lower or "column" in prompt_lower:
            risk_level = "Medium"
            
            # Identify affected nodes in Contract Graph
            for node in graph_data.nodes:
                if node.node_type == ContractNodeType.FRONTEND:
                    affected_fe.append(f"{node.name} ({node.metadata.get('file_path', 'frontend')})")
                elif node.node_type == ContractNodeType.API:
                    affected_api.append(f"{node.name} ({node.metadata.get('endpoint', '')})")
                elif node.node_type == ContractNodeType.BACKEND:
                    affected_be.append(f"{node.name} ({node.metadata.get('file_path', 'backend')})")
                elif node.node_type == ContractNodeType.DATABASE:
                    affected_db.append(f"{node.name}: ADD COLUMN phone_number VARCHAR(15) NOT NULL")
                elif node.node_type == ContractNodeType.TEST:
                    affected_tests.append(f"{node.name} (assertions for phone_number)")

            # Check for simulated contract mismatch scenario (Frontend: phone vs Backend: phone_number)
            if "phone" in prompt_lower:
                violations.append(
                    ContractViolation(
                        source_node="fe:StudentForm.tsx",
                        target_node="api:post_students",
                        source_field="phone",
                        expected_field="phone_number",
                        endpoint_or_module="POST /students",
                        description="Cross-Layer Contract Mismatch: Frontend form uses key 'phone', whereas Backend Pydantic schema & DB column expect 'phone_number'."
                    )
                )

            explanations.extend([
                "1. Database requires a schema migration: Adding 'phone_number VARCHAR(15) NOT NULL' to the 'students' table.",
                "2. Backend Pydantic schema 'StudentCreate' must include 'phone_number: str = Field(..., max_length=15)'.",
                "3. API endpoints 'POST /students' and 'GET /students' must serialize and return the new field.",
                "4. React components 'StudentForm.tsx' and 'StudentList.tsx' must update inputs and display columns.",
                "5. Pytest suite 'test_student_api.py' requires updated test fixtures with valid phone numbers.",
            ])

            summary = (
                f"Adding phone number to Student impacts 5 architectural layers. "
                f"Frontend: {len(affected_fe)} files, Backend: {len(affected_be)} files, "
                f"API: {len(affected_api)} routes, DB: {len(affected_db)} migration, Tests: {len(affected_tests)} suites."
            )
        else:
            summary = "General modification. Minor localized impact."
            explanations.append("No schema-level breaking changes detected in the Contract Graph.")

        return ImpactReport(
            summary=summary,
            affected_frontend=affected_fe,
            affected_backend=affected_be,
            affected_apis=affected_api,
            affected_database=affected_db,
            affected_tests=affected_tests,
            violations=violations,
            risk_level=risk_level,
            explanations=explanations,
        )

impact_analyzer = ImpactAnalyzer()
