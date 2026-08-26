import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import networkx as nx

from ..models.schemas import (
    ContractNode,
    ContractEdge,
    ContractNodeType,
    ContractNodeStatus,
    ContractGraphData,
    ContractViolation,
    ImpactReport,
)

logger = logging.getLogger("sugio_labs.contract_graph")


class ContractGraph:
    """
    Core Contract Graph Engine for Sugio Labs.
    Maintains semantic dependencies across Requirements, Frontend, API, Backend, Database, and Tests.
    Detects contract drifts and computes cross-layer impact.
    """

    def __init__(self):
        self._graph: nx.DiGraph = nx.DiGraph()
        self._nodes: Dict[str, ContractNode] = {}
        self._edges: List[ContractEdge] = []

    def clear(self):
        """Clears all nodes and edges in the graph."""
        self._graph.clear()
        self._nodes.clear()
        self._edges.clear()

    def add_node(self, node: ContractNode) -> ContractNode:
        """Adds or updates a node in the contract graph."""
        self._nodes[node.id] = node
        self._graph.add_node(
            node.id,
            name=node.name,
            layer=node.layer,
            node_type=node.node_type.value,
            metadata=node.metadata,
            status=node.status.value,
        )
        logger.debug(f"Added/Updated node: {node.id} ({node.name}) in layer {node.layer}")
        return node

    def get_node(self, node_id: str) -> Optional[ContractNode]:
        """Retrieves a node by its ID."""
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> bool:
        """Removes a node and its associated edges."""
        if node_id in self._nodes:
            del self._nodes[node_id]
            self._graph.remove_node(node_id)
            self._edges = [e for e in self._edges if e.source != node_id and e.target != node_id]
            logger.info(f"Removed node: {node_id}")
            return True
        return False

    def add_edge(self, edge: ContractEdge) -> ContractEdge:
        """Adds a directed dependency edge from source to target."""
        if edge.source not in self._nodes:
            raise ValueError(f"Source node '{edge.source}' does not exist in the Contract Graph.")
        if edge.target not in self._nodes:
            raise ValueError(f"Target node '{edge.target}' does not exist in the Contract Graph.")

        self._edges = [
            e for e in self._edges if not (e.source == edge.source and e.target == edge.target)
        ]
        self._edges.append(edge)
        self._graph.add_edge(
            edge.source,
            edge.target,
            relation_type=edge.relation_type,
            metadata=edge.metadata,
        )
        logger.debug(f"Added edge: {edge.source} -> {edge.target} ({edge.relation_type})")
        return edge

    def get_nodes_by_layer(self, layer: str) -> List[ContractNode]:
        """Returns all nodes belonging to a specific architectural layer."""
        return [node for node in self._nodes.values() if node.layer.lower() == layer.lower()]

    def get_dependencies(self, node_id: str) -> List[ContractNode]:
        """Returns nodes that this node depends on (successors in the DAG)."""
        if node_id not in self._graph:
            return []
        successor_ids = list(self._graph.successors(node_id))
        return [self._nodes[s_id] for s_id in successor_ids if s_id in self._nodes]

    def get_dependents(self, node_id: str) -> List[ContractNode]:
        """Returns nodes that depend on this node (predecessors in the DAG)."""
        if node_id not in self._graph:
            return []
        predecessor_ids = list(self._graph.predecessors(node_id))
        return [self._nodes[p_id] for p_id in predecessor_ids if p_id in self._nodes]

    def get_transitive_impact(self, node_id: str) -> Set[str]:
        """Computes all reachable downstream and upstream affected nodes."""
        if node_id not in self._graph:
            return set()
        
        # Descendants (nodes that depend downstream on this node or flow from this node)
        downstream = nx.descendants(self._graph, node_id)
        # Ancestors (nodes upstream that might trigger or be affected)
        upstream = nx.ancestors(self._graph, node_id)
        return downstream.union(upstream).union({node_id})

    def find_violations(self) -> List[ContractViolation]:
        """
        Inspects all connected edges across layers to verify consistency:
        - Frontend payload fields match API request schemas.
        - API parameters match Backend handler signatures.
        - Backend models match Database column names and types.
        - Test assertions cover all declared fields.
        """
        violations: List[ContractViolation] = []

        for edge in self._edges:
            source_node = self._nodes.get(edge.source)
            target_node = self._nodes.get(edge.target)

            if not source_node or not target_node:
                continue

            src_fields = source_node.metadata.get("fields", {})
            tgt_fields = target_node.metadata.get("fields", {})

            # Case: Dict of field_name -> field_type
            if isinstance(src_fields, dict) and isinstance(tgt_fields, dict):
                for f_name, f_type in src_fields.items():
                    # Check for renamed or missing fields
                    if f_name not in tgt_fields:
                        # Check if a similarly named field exists (e.g. phone vs phone_number)
                        similar = [k for k in tgt_fields.keys() if f_name in k or k in f_name]
                        desc = f"Field '{f_name}' in {source_node.name} is missing in {target_node.name}."
                        if similar:
                            desc += f" Possible mismatch with '{similar[0]}'."

                        violations.append(
                            ContractViolation(
                                source_node=source_node.id,
                                target_node=target_node.id,
                                source_field=f_name,
                                expected_field=similar[0] if similar else f_name,
                                endpoint_or_module=f"{source_node.name} -> {target_node.name}",
                                description=desc,
                            )
                        )
                    elif f_type and tgt_fields[f_name] and f_type.lower() != str(tgt_fields[f_name]).lower():
                        violations.append(
                            ContractViolation(
                                source_node=source_node.id,
                                target_node=target_node.id,
                                source_field=f"{f_name}:{f_type}",
                                expected_field=f"{f_name}:{tgt_fields[f_name]}",
                                endpoint_or_module=f"{source_node.name} -> {target_node.name}",
                                description=f"Type mismatch for field '{f_name}': {source_node.name} has '{f_type}' while {target_node.name} expects '{tgt_fields[f_name]}'.",
                            )
                        )

        return violations

    def analyze_impact(self, target_identifier: str, proposed_change: Dict[str, Any]) -> ImpactReport:
        """
        Performs cross-layer impact analysis when a change is requested.
        Maps the blast radius across Frontend, Backend, API, Database, and Tests.
        """
        # Find matching node by id, name, or metadata field
        matching_nodes: List[str] = []
        for nid, node in self._nodes.items():
            if (
                nid.lower() == target_identifier.lower()
                or node.name.lower() == target_identifier.lower()
                or target_identifier.lower() in [k.lower() for k in node.metadata.get("fields", {}).keys()]
            ):
                matching_nodes.append(nid)

        if not matching_nodes:
            # If graph is empty or node not found, fallback gracefully
            return ImpactReport(
                summary=f"No existing contract graph nodes found for '{target_identifier}'. New nodes will be constructed.",
                risk_level="Low",
                explanations=[f"Target entity '{target_identifier}' does not conflict with existing contracts."],
            )

        all_affected_ids: Set[str] = set()
        for nid in matching_nodes:
            all_affected_ids.update(self.get_transitive_impact(nid))

        affected_fe: List[str] = []
        affected_be: List[str] = []
        affected_api: List[str] = []
        affected_db: List[str] = []
        affected_tests: List[str] = []

        for nid in all_affected_ids:
            node = self._nodes[nid]
            layer = node.layer.lower()
            label = f"{node.name} ({node.id})"
            if "front" in layer:
                affected_fe.append(label)
            elif "api" in layer:
                affected_api.append(label)
            elif "back" in layer:
                affected_be.append(label)
            elif "data" in layer or "db" in layer:
                affected_db.append(label)
            elif "test" in layer:
                affected_tests.append(label)

        # Detect violations
        violations = self.find_violations()

        # Compute risk level
        risk = "Low"
        if affected_db or len(affected_api) > 1 or len(violations) > 0:
            risk = "High" if (affected_db and affected_api and affected_fe) else "Medium"

        explanations = [
            f"Modifying '{target_identifier}' impacts {len(all_affected_ids)} contract node(s) across {len({self._nodes[n].layer for n in all_affected_ids})} layer(s).",
        ]
        if affected_db:
            explanations.append("Database schema migration and field persistence updates required.")
        if affected_api:
            explanations.append("API route schema validation updates required.")
        if affected_fe:
            explanations.append("Frontend form components and API service call payload updates required.")
        if affected_tests:
            explanations.append("Test assertions and mocks must be synchronized.")

        return ImpactReport(
            summary=f"Impact Analysis for '{target_identifier}': {len(all_affected_ids)} node(s) across full stack.",
            affected_frontend=affected_fe,
            affected_backend=affected_be,
            affected_apis=affected_api,
            affected_database=affected_db,
            affected_tests=affected_tests,
            violations=violations,
            risk_level=risk,
            explanations=explanations,
        )

    def export_graph(self) -> ContractGraphData:
        """Serializes current graph to ContractGraphData schema."""
        return ContractGraphData(
            nodes=list(self._nodes.values()),
            edges=self._edges,
        )

    def import_graph(self, data: ContractGraphData):
        """Loads nodes and edges from ContractGraphData."""
        self.clear()
        for node in data.nodes:
            self.add_node(node)
        for edge in data.edges:
            self.add_edge(edge)

    def to_json(self) -> str:
        """Exports graph to JSON string."""
        data = self.export_graph()
        return data.model_dump_json(indent=2)

    def from_json(self, json_str: str):
        """Loads graph from JSON string."""
        raw = json.loads(json_str)
        data = ContractGraphData(**raw)
        self.import_graph(data)

    def save_to_file(self, filepath: Path):
        """Persists graph to JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(self.to_json(), encoding="utf-8")

    def load_from_file(self, filepath: Path):
        """Loads graph from JSON file if it exists."""
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            self.from_json(content)

    def build_sample_graph(self):
        """Constructs a standard reference Contract Graph (Student Management System)."""
        self.clear()

        # 1. Requirement Node
        req_student = ContractNode(
            id="req:manage_students",
            name="Student Profile Management",
            layer="Requirement",
            node_type=ContractNodeType.REQUIREMENT,
            metadata={"description": "Create, list, and update student profiles with name, email, roll_number, course, and phone."},
            status=ContractNodeStatus.SYNCHRONIZED,
        )

        # 2. Frontend Component Node
        fe_form = ContractNode(
            id="fe:StudentForm.tsx",
            name="StudentForm Component",
            layer="Frontend",
            node_type=ContractNodeType.FRONTEND,
            metadata={
                "component": "StudentForm",
                "fields": {
                    "name": "string",
                    "email": "string",
                    "roll_number": "string",
                    "course": "string",
                    "phone": "string",
                },
            },
            status=ContractNodeStatus.SYNCHRONIZED,
        )

        # 3. API Endpoint Node
        api_post = ContractNode(
            id="api:post_students",
            name="POST /api/v1/students",
            layer="API",
            node_type=ContractNodeType.API,
            metadata={
                "method": "POST",
                "path": "/api/v1/students",
                "fields": {
                    "name": "string",
                    "email": "string",
                    "roll_number": "string",
                    "course": "string",
                    "phone": "string",
                },
            },
            status=ContractNodeStatus.SYNCHRONIZED,
        )

        # 4. Backend Service Node
        be_service = ContractNode(
            id="be:StudentService",
            name="StudentService.create_student",
            layer="Backend",
            node_type=ContractNodeType.BACKEND,
            metadata={
                "class": "StudentService",
                "method": "create_student",
                "fields": {
                    "name": "str",
                    "email": "str",
                    "roll_number": "str",
                    "course": "str",
                    "phone": "str",
                },
            },
            status=ContractNodeStatus.SYNCHRONIZED,
        )

        # 5. Database Schema Node
        db_table = ContractNode(
            id="db:students_table",
            name="students (PostgreSQL Table)",
            layer="Database",
            node_type=ContractNodeType.DATABASE,
            metadata={
                "table_name": "students",
                "fields": {
                    "id": "INTEGER PRIMARY KEY",
                    "name": "VARCHAR(255) NOT NULL",
                    "email": "VARCHAR(255) UNIQUE NOT NULL",
                    "roll_number": "VARCHAR(50) UNIQUE NOT NULL",
                    "course": "VARCHAR(100) NOT NULL",
                    "phone": "VARCHAR(20)",
                },
            },
            status=ContractNodeStatus.SYNCHRONIZED,
        )

        # 6. Test Suite Node
        test_suite = ContractNode(
            id="test:test_student_creation",
            name="test_create_student (Pytest + Vitest)",
            layer="Test",
            node_type=ContractNodeType.TEST,
            metadata={
                "test_file": "test_students.py",
                "fields": {
                    "name": "valid",
                    "email": "valid",
                    "roll_number": "valid",
                    "course": "valid",
                    "phone": "valid",
                },
            },
            status=ContractNodeStatus.SYNCHRONIZED,
        )

        # Add all nodes
        for n in [req_student, fe_form, api_post, be_service, db_table, test_suite]:
            self.add_node(n)

        # Add connecting dependency edges
        self.add_edge(ContractEdge(source=req_student.id, target=fe_form.id, relation_type="specifies"))
        self.add_edge(ContractEdge(source=fe_form.id, target=api_post.id, relation_type="invokes"))
        self.add_edge(ContractEdge(source=api_post.id, target=be_service.id, relation_type="routes_to"))
        self.add_edge(ContractEdge(source=be_service.id, target=db_table.id, relation_type="persists"))
        self.add_edge(ContractEdge(source=db_table.id, target=test_suite.id, relation_type="validated_by"))
        self.add_edge(ContractEdge(source=api_post.id, target=test_suite.id, relation_type="tested_by"))

        logger.info("Built reference Student Management System Contract Graph with 6 nodes and 6 edges.")


contract_graph = ContractGraph()
contract_graph.build_sample_graph()
