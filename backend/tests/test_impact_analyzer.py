import pytest
from app.agents.impact_analyzer import ImpactAnalyzer
from app.contract_graph.graph import contract_graph_engine

def test_impact_analysis_on_student_change():
    contract_graph_engine.populate_student_demo_graph()
    analyzer = ImpactAnalyzer()
    
    report = analyzer.analyze_change("Add mandatory phone number to Student")
    
    assert report.risk_level in ["Medium", "High"]
    assert len(report.affected_frontend) >= 1
    assert len(report.affected_backend) >= 1
    assert len(report.affected_apis) >= 1
    assert len(report.affected_database) >= 1
    assert len(report.affected_tests) >= 1
    assert len(report.violations) >= 1
