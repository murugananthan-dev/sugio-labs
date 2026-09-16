import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import networkx as nx

from ..models.schemas import (
    ContractEdge,
    ContractGraphData,
    ContractNode,
    ContractNodeStatus,
    ContractNodeType,
    ContractViolation,
    ImpactReport,
    ProjectBlueprint,
)

logger = logging.getLogger("sugio_labs.contract_graph")


class ContractGraph:
    """Cross-layer dependency graph used for drift detection and impact analysis."""

    def __init__(self):
        self._graph: nx.DiGraph = nx.DiGraph()
        self._nodes: Dict[str, ContractNode] = {}
        self._edges: List[ContractEdge] = []

    def clear(self):
        self._graph.clear()
        self._nodes.clear()
        self._edges.clear()

    def add_node(self, node: ContractNode) -> ContractNode:
        self._nodes[node.id] = node
        self._graph.add_node(
            node.id,
            name=node.name,
            layer=node.layer,
            node_type=node.node_type.value,
            metadata=node.metadata,
            status=node.status.value,
        )
        return node

    def get_node(self, node_id: str) -> Optional[ContractNode]:
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        self._graph.remove_node(node_id)
        self._edges = [edge for edge in self._edges if edge.source != node_id and edge.target != node_id]
        return True

    def add_edge(self, edge: ContractEdge) -> ContractEdge:
        if edge.source not in self._nodes:
            raise ValueError(f"Source node '{edge.source}' does not exist in the Contract Graph.")
        if edge.target not in self._nodes:
            raise ValueError(f"Target node '{edge.target}' does not exist in the Contract Graph.")

        self._edges = [
            existing
            for existing in self._edges
            if not (existing.source == edge.source and existing.target == edge.target)
        ]
        self._edges.append(edge)
        self._graph.add_edge(
            edge.source,
            edge.target,
            relation_type=edge.relation_type,
            metadata=edge.metadata,
        )
        return edge

    def get_nodes_by_layer(self, layer: str) -> List[ContractNode]:
        return [node for node in self._nodes.values() if node.layer.lower() == layer.lower()]

    def get_dependencies(self, node_id: str) -> List[ContractNode]:
        if node_id not in self._graph:
            return []
        return [self._nodes[node] for node in self._graph.successors(node_id) if node in self._nodes]

    def get_dependents(self, node_id: str) -> List[ContractNode]:
        if node_id not in self._graph:
            return []
        return [self._nodes[node] for node in self._graph.predecessors(node_id) if node in self._nodes]

    def get_transitive_impact(self, node_id: str) -> Set[str]:
        if node_id not in self._graph:
            return set()
        return nx.descendants(self._graph, node_id).union(nx.ancestors(self._graph, node_id)).union({node_id})

    def find_violations(self) -> List[ContractViolation]:
        violations: List[ContractViolation] = []
        for edge in self._edges:
            source = self._nodes.get(edge.source)
            target = self._nodes.get(edge.target)
            if not source or not target:
                continue

            source_fields = source.metadata.get("fields", {})
            target_fields = target.metadata.get("fields", {})
            if not isinstance(source_fields, dict) or not isinstance(target_fields, dict):
                continue

            for field_name, field_type in source_fields.items():
                if field_name not in target_fields:
                    similar = [name for name in target_fields if field_name in name or name in field_name]
                    violations.append(
                        ContractViolation(
                            source_node=source.id,
                            target_node=target.id,
                            source_field=field_name,
                            expected_field=similar[0] if similar else field_name,
                            endpoint_or_module=f"{source.name} -> {target.name}",
                            description=(
                                f"Field '{field_name}' in {source.name} is missing in {target.name}."
                                + (f" Possible mismatch with '{similar[0]}'." if similar else "")
                            ),
                        )
                    )
                    continue

                target_type = target_fields[field_name]
                if field_type and target_type and str(field_type).lower() != str(target_type).lower():
                    # Common Python/TypeScript aliases should not create noisy violations.
                    aliases = {
                        "str": "string",
                        "string": "string",
                        "int": "integer",
                        "integer": "integer",
                        "float": "number",
                        "number": "number",
                        "bool": "boolean",
                        "boolean": "boolean",
                    }
                    if aliases.get(str(field_type).lower(), str(field_type).lower()) == aliases.get(str(target_type).lower(), str(target_type).lower()):
                        continue
                    violations.append(
                        ContractViolation(
                            source_node=source.id,
                            target_node=target.id,
                            source_field=f"{field_name}:{field_type}",
                            expected_field=f"{field_name}:{target_type}",
                            endpoint_or_module=f"{source.name} -> {target.name}",
                            description=f"Type mismatch for '{field_name}': {source.name} has '{field_type}' while {target.name} expects '{target_type}'.",
                        )
                    )
        return violations

    def _matching_nodes(self, identifier: str) -> List[str]:
        needle = identifier.strip().lower()
        if not needle:
            return []

        direct: List[str] = []
        fuzzy: List[str] = []
        for node_id, node in self._nodes.items():
            fields = node.metadata.get("fields", {})
            field_names = [str(name).lower() for name in fields] if isinstance(fields, dict) else []
            if needle == node_id.lower() or needle == node.name.lower() or needle in field_names:
                direct.append(node_id)
                continue

            searchable = " ".join([
                node_id.lower(),
                node.name.lower(),
                node.layer.lower(),
                json.dumps(node.metadata, default=str).lower(),
            ])
            if needle in searchable or any(token and token in searchable for token in needle.split()):
                fuzzy.append(node_id)

        return direct or fuzzy

    def analyze_impact(self, target_identifier: str, proposed_change: Dict[str, Any]) -> ImpactReport:
        matching_nodes = self._matching_nodes(target_identifier)
        if not matching_nodes:
            return ImpactReport(
                summary=f"No current contract matches '{target_identifier}'. The change can be treated as a new contract until implementation adds dependencies.",
                risk_level="Low",
                explanations=[
                    f"'{target_identifier}' is not present in the current graph.",
                    "Create or update graph nodes when the implementation introduces this contract.",
                ],
            )

        affected_ids: Set[str] = set()
        for node_id in matching_nodes:
            affected_ids.update(self.get_transitive_impact(node_id))

        affected_frontend: List[str] = []
        affected_backend: List[str] = []
        affected_apis: List[str] = []
        affected_database: List[str] = []
        affected_tests: List[str] = []

        for node_id in sorted(affected_ids):
            node = self._nodes[node_id]
            label = f"{node.name} ({node.id})"
            layer = node.layer.lower()
            if "front" in layer:
                affected_frontend.append(label)
            elif "api" in layer:
                affected_apis.append(label)
            elif "back" in layer:
                affected_backend.append(label)
            elif "data" in layer or "db" in layer:
                affected_database.append(label)
            elif "test" in layer:
                affected_tests.append(label)

        violations = self.find_violations()
        layer_count = len({self._nodes[node_id].layer for node_id in affected_ids})

        risk = "Low"
        if len(affected_ids) >= 4 or affected_database or violations:
            risk = "Medium"
        if affected_frontend and affected_apis and affected_backend and affected_database:
            risk = "High"

        explanations = [
            f"The change touches {len(affected_ids)} contract node(s) across {layer_count} architectural layer(s)."
        ]
        if affected_frontend:
            explanations.append("Frontend forms, payloads, or service calls may need synchronized updates.")
        if affected_apis:
            explanations.append("API request/response contracts or routes are in the blast radius.")
        if affected_backend:
            explanations.append("Backend service or validation behavior is connected to this contract.")
        if affected_database:
            explanations.append("Persistence changes may require a schema migration and rollback plan.")
        if affected_tests:
            explanations.append("Automated tests and fixtures should be updated in the same change set.")
        if violations:
            explanations.append(f"The current graph already contains {len(violations)} contract drift warning(s).")

        return ImpactReport(
            summary=f"Impact analysis for '{target_identifier}': {len(affected_ids)} connected node(s).",
            affected_frontend=affected_frontend,
            affected_backend=affected_backend,
            affected_apis=affected_apis,
            affected_database=affected_database,
            affected_tests=affected_tests,
            violations=violations,
            risk_level=risk,
            explanations=explanations,
        )

    def export_graph(self) -> ContractGraphData:
        return ContractGraphData(nodes=list(self._nodes.values()), edges=self._edges)

    def import_graph(self, data: ContractGraphData):
        self.clear()
        for node in data.nodes:
            self.add_node(node)
        for edge in data.edges:
            self.add_edge(edge)

    def to_json(self) -> str:
        return self.export_graph().model_dump_json(indent=2)

    def from_json(self, json_str: str):
        self.import_graph(ContractGraphData(**json.loads(json_str)))

    def save_to_file(self, filepath: Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(self.to_json(), encoding="utf-8")

    def load_from_file(self, filepath: Path):
        if filepath.exists():
            self.from_json(filepath.read_text(encoding="utf-8"))

    @staticmethod
    def _slug(value: str) -> str:
        return "_".join("".join(char.lower() if char.isalnum() else " " for char in value).split())[:72] or "node"

    def build_from_blueprint(self, blueprint: ProjectBlueprint):
        """Build a project-specific graph from the approved architecture blueprint."""
        self.clear()

        requirement = ContractNode(
            id="req:project",
            name=blueprint.project_name,
            layer="Requirement",
            node_type=ContractNodeType.REQUIREMENT,
            metadata={
                "objective": blueprint.objective,
                "features": blueprint.features,
                "roles": blueprint.user_roles,
                "requirements": blueprint.functional_requirements,
            },
            status=ContractNodeStatus.SYNCHRONIZED,
        )
        self.add_node(requirement)

        frontend_ids: List[str] = []
        for module in blueprint.frontend_modules:
            node_id = f"fe:{self._slug(str(module.get('name', 'module')))}"
            self.add_node(ContractNode(
                id=node_id,
                name=str(module.get("name", "Frontend module")),
                layer="Frontend",
                node_type=ContractNodeType.FRONTEND,
                metadata={"path": module.get("path"), "purpose": module.get("purpose")},
                status=ContractNodeStatus.SYNCHRONIZED,
            ))
            frontend_ids.append(node_id)

        api_ids: List[str] = []
        for endpoint in blueprint.api_endpoints:
            method = str(endpoint.get("method", "GET"))
            path = str(endpoint.get("path", "/"))
            node_id = f"api:{self._slug(method + '_' + path)}"
            self.add_node(ContractNode(
                id=node_id,
                name=f"{method} {path}",
                layer="API",
                node_type=ContractNodeType.API,
                metadata={"method": method, "path": path, "description": endpoint.get("description")},
                status=ContractNodeStatus.SYNCHRONIZED,
            ))
            api_ids.append(node_id)

        backend_ids: List[str] = []
        for module in blueprint.backend_modules:
            node_id = f"be:{self._slug(str(module.get('name', 'module')))}"
            self.add_node(ContractNode(
                id=node_id,
                name=str(module.get("name", "Backend module")),
                layer="Backend",
                node_type=ContractNodeType.BACKEND,
                metadata={"path": module.get("path"), "purpose": module.get("purpose")},
                status=ContractNodeStatus.SYNCHRONIZED,
            ))
            backend_ids.append(node_id)

        database_ids: List[str] = []
        for schema in blueprint.db_schema:
            table = str(schema.get("table", "table"))
            columns = schema.get("columns", [])
            fields: Dict[str, str] = {}
            for column in columns:
                if isinstance(column, str):
                    parts = column.split(maxsplit=1)
                    fields[parts[0]] = parts[1] if len(parts) > 1 else "unknown"
                elif isinstance(column, dict) and column.get("name"):
                    fields[str(column["name"])] = str(column.get("type", "unknown"))
            node_id = f"db:{self._slug(table)}"
            self.add_node(ContractNode(
                id=node_id,
                name=table,
                layer="Database",
                node_type=ContractNodeType.DATABASE,
                metadata={"table_name": table, "fields": fields},
                status=ContractNodeStatus.SYNCHRONIZED,
            ))
            database_ids.append(node_id)

        test_id = "test:verification"
        self.add_node(ContractNode(
            id=test_id,
            name="Project verification suite",
            layer="Test",
            node_type=ContractNodeType.TEST,
            metadata={"strategy": blueprint.testing_strategy, "features": blueprint.features},
            status=ContractNodeStatus.SYNCHRONIZED,
        ))

        for frontend_id in frontend_ids:
            self.add_edge(ContractEdge(source=requirement.id, target=frontend_id, relation_type="specifies"))
        if not frontend_ids:
            for api_id in api_ids:
                self.add_edge(ContractEdge(source=requirement.id, target=api_id, relation_type="specifies"))

        for frontend_id in frontend_ids:
            for api_id in api_ids:
                self.add_edge(ContractEdge(source=frontend_id, target=api_id, relation_type="invokes"))
        for api_id in api_ids:
            for backend_id in backend_ids:
                self.add_edge(ContractEdge(source=api_id, target=backend_id, relation_type="routes_to"))
            self.add_edge(ContractEdge(source=api_id, target=test_id, relation_type="tested_by"))
        for backend_id in backend_ids:
            for database_id in database_ids:
                self.add_edge(ContractEdge(source=backend_id, target=database_id, relation_type="persists"))
        for database_id in database_ids:
            self.add_edge(ContractEdge(source=database_id, target=test_id, relation_type="validated_by"))

        logger.info("Built blueprint Contract Graph with %s nodes and %s edges", len(self._nodes), len(self._edges))

    def build_sample_graph(self):
        """Reference graph retained for demos and regression tests."""
        self.clear()

        req_student = ContractNode(
            id="req:manage_students",
            name="Student Profile Management",
            layer="Requirement",
            node_type=ContractNodeType.REQUIREMENT,
            metadata={"description": "Create, list, and update student profiles with name, email, roll_number, course, and phone."},
            status=ContractNodeStatus.SYNCHRONIZED,
        )
        fe_form = ContractNode(
            id="fe:StudentForm.tsx",
            name="StudentForm Component",
            layer="Frontend",
            node_type=ContractNodeType.FRONTEND,
            metadata={"component": "StudentForm", "fields": {"name": "string", "email": "string", "roll_number": "string", "course": "string", "phone": "string"}},
            status=ContractNodeStatus.SYNCHRONIZED,
        )
        api_post = ContractNode(
            id="api:post_students",
            name="POST /api/v1/students",
            layer="API",
            node_type=ContractNodeType.API,
            metadata={"method": "POST", "path": "/api/v1/students", "fields": {"name": "string", "email": "string", "roll_number": "string", "course": "string", "phone": "string"}},
            status=ContractNodeStatus.SYNCHRONIZED,
        )
        be_service = ContractNode(
            id="be:StudentService",
            name="StudentService.create_student",
            layer="Backend",
            node_type=ContractNodeType.BACKEND,
            metadata={"class": "StudentService", "method": "create_student", "fields": {"name": "str", "email": "str", "roll_number": "str", "course": "str", "phone": "str"}},
            status=ContractNodeStatus.SYNCHRONIZED,
        )
        db_table = ContractNode(
            id="db:students_table",
            name="students (PostgreSQL Table)",
            layer="Database",
            node_type=ContractNodeType.DATABASE,
            metadata={"table_name": "students", "fields": {"id": "INTEGER PRIMARY KEY", "name": "VARCHAR(255) NOT NULL", "email": "VARCHAR(255) UNIQUE NOT NULL", "roll_number": "VARCHAR(50) UNIQUE NOT NULL", "course": "VARCHAR(100) NOT NULL", "phone": "VARCHAR(20)"}},
            status=ContractNodeStatus.SYNCHRONIZED,
        )
        test_suite = ContractNode(
            id="test:test_student_creation",
            name="test_create_student (Pytest + Vitest)",
            layer="Test",
            node_type=ContractNodeType.TEST,
            metadata={"test_file": "test_students.py", "fields": {"name": "valid", "email": "valid", "roll_number": "valid", "course": "valid", "phone": "valid"}},
            status=ContractNodeStatus.SYNCHRONIZED,
        )

        for node in [req_student, fe_form, api_post, be_service, db_table, test_suite]:
            self.add_node(node)

        self.add_edge(ContractEdge(source=req_student.id, target=fe_form.id, relation_type="specifies"))
        self.add_edge(ContractEdge(source=fe_form.id, target=api_post.id, relation_type="invokes"))
        self.add_edge(ContractEdge(source=api_post.id, target=be_service.id, relation_type="routes_to"))
        self.add_edge(ContractEdge(source=be_service.id, target=db_table.id, relation_type="persists"))
        self.add_edge(ContractEdge(source=db_table.id, target=test_suite.id, relation_type="validated_by"))
        self.add_edge(ContractEdge(source=api_post.id, target=test_suite.id, relation_type="tested_by"))


contract_graph = ContractGraph()
contract_graph.build_sample_graph()
