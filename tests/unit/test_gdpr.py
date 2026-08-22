"""Unit tests for KAVP GDPR module."""
import pytest
from kavp.gdpr import (
    PolicyGraph, Node, Edge, NodeType, EdgeType,
    Constraint, ClientProfile, DefeasibleResolver, Rule, Modality,
    EvidenceStore, VersionHandler, compile_controls, required_evidence,
    feasibility, compliance, cost, transfer_admissible, Decision
)
from kavp.gdpr.policies import build_gdpr_graph, build_org_override_graph


def test_gdpr_graph_nodes():
    g = build_gdpr_graph()
    assert len(g.nodes) > 0


def test_applicable_constraints():
    g = build_gdpr_graph()
    profile = ClientProfile(
        cid="c0", jurisdiction="EU", region="EU", domain="healthcare",
        data_categories=["health"], legal_basis="art6_1_e", art9_condition="9_2_h",
        consent_valid=True, transfer_mechanism="adequacy", epsilon_remaining=8.0,
        purpose_id="task-001", declared_features=[f"f{i}" for i in range(8)],
        approved_features=[f"f{i}" for i in range(8)], retention_ok=True,
        dpia_done=True, is_controller=True, processor_scope=["agg"]
    )
    cons = g.applicable_constraints(profile)
    assert len(cons) > 0


def test_feasibility():
    g = build_gdpr_graph()
    profile = ClientProfile(
        cid="c0", jurisdiction="EU", region="EU", domain="healthcare",
        data_categories=["health"], legal_basis="art6_1_e", art9_condition="9_2_h",
        consent_valid=True, transfer_mechanism="adequacy", epsilon_remaining=8.0,
        purpose_id="task-001", declared_features=[f"f{i}" for i in range(8)],
        approved_features=[f"f{i}" for i in range(8)], retention_ok=True,
        dpia_done=True, is_controller=True, processor_scope=["agg"]
    )
    cons = g.applicable_constraints(profile)
    f = feasibility(profile, cons, tau=1.0, kappa_max=0.0)
    assert f == 1


def test_defeasible_resolver():
    g = build_org_override_graph()
    resolver = DefeasibleResolver(g)
    rules = [
        Rule("r_art9", Modality.OBLIGATION, "special_cat", "GDPR", 3.0),
        Rule("r_org07", Modality.PERMISSION, "special_cat", "ORG", 0.5),
    ]
    undefeated, defeats = resolver.resolve(rules)
    assert "r_art9" in {r.rid for r in undefeated}


def test_evidence_store_integrity():
    store = EvidenceStore()
    decision = Decision(
        decision="allowed", cid="c0", round=0, purpose="t1", jurisdiction="EU",
        applicable=[], controls=[], violated=[], defeated=[],
        human_review=False, policy_version=1, evidence_ids=[], explanation_id="exp-0",
        timestamp=0.0, transfer_admissible=True, consent_state="valid"
    )
    ev1, h1 = store.record(decision, [], ["a"])
    ev2, h2 = store.record(decision, [], ["b"])
    assert store.integrity_ok()
    assert store.audit_completeness() == 1.0


def test_version_handler():
    g1 = build_gdpr_graph(version=1)
    g2 = build_gdpr_graph(version=2)
    handler = VersionHandler(g1)
    decisions = []
    mig = handler.migrate(g2, decisions)
    assert mig["from"] == 1
    assert mig["to"] == 2


def test_compile_controls():
    controls = compile_controls(["6", "7", "9"])
    assert "lawful_basis_check" in controls


def test_transfer_admissible():
    assert transfer_admissible("EU", "EU", "adequacy") is True
    assert transfer_admissible("US", "EU", "scc") is True
    assert transfer_admissible("US", "IN", "none") is False
