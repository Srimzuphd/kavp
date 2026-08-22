"""Unit tests for KAVP core modules."""
import pytest
from kavp.core.policy_ingestion import PolicyIngestion, SamplePolicies
from kavp.core.parser import PolicyParser
from kavp.core.graph_builder import GraphBuilder
from kavp.core.constraint_engine import ConstraintPropagation, NodeProfile
from kavp.core.orchestrator import FederatedOrchestrator, DemoNodeFactory
from kavp.core.audit_logger import AuditLogger


def test_policy_ingestion_loads_scenario():
    ingestion = PolicyIngestion()
    policies = ingestion.load_scenario("healthcare")
    assert len(policies) == len(SamplePolicies.HEALTHCARE)
    assert policies[0].source_id.startswith("POL-")


def test_policy_parser_extracts_entities():
    parser = PolicyParser()
    parsed = parser.parse("T1", "EU patient data cannot leave EU region")
    assert len(parsed.entities) > 0
    assert len(parsed.constraints) > 0


def test_graph_builder_creates_nodes():
    parser = PolicyParser()
    parsed = [parser.parse("P1", "EU patient data cannot leave EU region")]
    builder = GraphBuilder()
    graph = builder.build_graph(parsed, "g1")
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0


def test_constraint_engine_evaluates_node():
    parser = PolicyParser()
    parsed = [parser.parse("P1", "EU patient data cannot leave EU region")]
    builder = GraphBuilder()
    builder.build_graph(parsed, "g1")
    engine = ConstraintPropagation(builder)
    node = NodeProfile(node_id="N1", name="Node 1", region="US", domain="healthcare",
                       compliance_tags=["HIPAA"])
    result = engine.evaluate_node(node, parsed)
    assert result.node_id == "N1"
    assert isinstance(result.eligible, bool)


def test_orchestrator_creates_task():
    parser = PolicyParser()
    parsed = [parser.parse("P1", "EU patient data cannot leave EU region")]
    builder = GraphBuilder()
    builder.build_graph(parsed, "g1")
    engine = ConstraintPropagation(builder)
    orchestrator = FederatedOrchestrator(builder)
    nodes = DemoNodeFactory.get_nodes("healthcare")
    orchestrator.register_nodes(nodes)
    results = engine.evaluate_all_nodes(nodes, parsed)
    task = orchestrator.create_task("Test", results)
    assert task.task_id is not None


def test_audit_logger_records_events():
    logger = AuditLogger()
    event = logger.log("test", "cat", "ok", "details")
    assert event.event_id is not None
    assert len(logger.events) == 1
    summary = logger.get_summary()
    assert summary["total_events"] == 1


def test_gdpr_policies_build_graph():
    from kavp.gdpr.policies import build_gdpr_graph
    g = build_gdpr_graph()
    assert len(g.nodes) > 0
