from app.agents.requirement_agent import requirement_agent
from app.contract_graph.graph import ContractGraph


def test_ecommerce_blueprint_changes_domain_artifacts():
    blueprint = requirement_agent.generate_blueprint_from_answers({
        "Q1_PROJECT_DOMAIN": "E-Commerce & Inventory Management",
        "Q2_USER_ROLES": "Role-Based Access Control (Admin, Manager, Member, Viewer)",
        "Q3_CORE_FEATURES": "Product Catalog, Shopping Cart, Order Checkout, Payment Simulation, Inventory Sync",
        "Q4_FRONTEND_STACK": "React (TypeScript + Vite + App Workspace UI)",
        "Q5_BACKEND_STACK": "FastAPI (Python async + Pydantic validation)",
        "Q6_DATABASE_STACK": "PostgreSQL (with SQLite fallback for lightweight local dev)",
        "Q7_TESTING_STRATEGY": "Pytest (Backend API + Unit) & Vitest (Frontend Components) + Contract Graph Validation",
    })

    assert blueprint.project_name == "E-Commerce & Inventory Management"
    assert any(module["name"] == "ProductForm" for module in blueprint.frontend_modules)
    assert any(endpoint["path"] == "/api/v1/products" for endpoint in blueprint.api_endpoints)
    assert blueprint.db_schema[0]["table"] == "products"


def test_contract_graph_is_generated_from_blueprint():
    blueprint = requirement_agent.generate_blueprint_from_answers({})
    graph = ContractGraph()
    graph.build_from_blueprint(blueprint)

    exported = graph.export_graph()
    node_types = {node.node_type.value for node in exported.nodes}

    assert {"requirement", "frontend", "api", "backend", "database", "test"}.issubset(node_types)
    assert len(exported.edges) > 0

    impact = graph.analyze_impact("Student", {"description": "Add emergency contact"})
    assert impact.affected_frontend
    assert impact.affected_apis
    assert impact.affected_backend
    assert impact.affected_database
