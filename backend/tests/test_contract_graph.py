import pytest
from app.contract_graph.graph import ContractGraph
from app.models.schemas import (
    ContractNode,
    ContractEdge,
    ContractNodeType,
    ContractNodeStatus,
)


def test_contract_graph_creation():
    graph = ContractGraph()
    graph.build_sample_graph()

    exported = graph.export_graph()
    assert len(exported.nodes) == 6
    assert len(exported.edges) == 6

    # Verify layer queries
    fe_nodes = graph.get_nodes_by_layer("Frontend")
    assert len(fe_nodes) == 1
    assert fe_nodes[0].id == "fe:StudentForm.tsx"

    db_nodes = graph.get_nodes_by_layer("Database")
    assert len(db_nodes) == 1
    assert db_nodes[0].id == "db:students_table"


def test_contract_violation_detection():
    graph = ContractGraph()

    # Add frontend node expecting 'phone_number'
    fe = ContractNode(
        id="fe:form",
        name="Form",
        layer="Frontend",
        node_type=ContractNodeType.FRONTEND,
        metadata={"fields": {"name": "string", "phone_number": "string"}},
    )

    # Add API node expecting 'phone'
    api = ContractNode(
        id="api:route",
        name="API",
        layer="API",
        node_type=ContractNodeType.API,
        metadata={"fields": {"name": "string", "phone": "string"}},
    )

    graph.add_node(fe)
    graph.add_node(api)
    graph.add_edge(ContractEdge(source=fe.id, target=api.id, relation_type="invokes"))

    violations = graph.find_violations()
    assert len(violations) > 0
    assert "phone_number" in violations[0].description or "phone" in violations[0].description


def test_impact_analysis():
    graph = ContractGraph()
    graph.build_sample_graph()

    impact = graph.analyze_impact("phone", {"change": "add phone to students"})
    assert impact.risk_level in ["Low", "Medium", "High"]
    assert len(impact.affected_frontend) > 0
    assert len(impact.affected_apis) > 0
    assert len(impact.affected_backend) > 0
    assert len(impact.affected_database) > 0
