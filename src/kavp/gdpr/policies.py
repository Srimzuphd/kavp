"""GDPR typed policy graph construction."""
from __future__ import annotations
from typing import List
from kavp.gdpr import (PolicyGraph, Node, Edge, NodeType, EdgeType,
                        Constraint, ClientProfile)


def _has_legal_basis(c: ClientProfile) -> bool:
    return c.legal_basis not in ("", "none")


def _has_art9_condition(c: ClientProfile) -> bool:
    sc = {"health", "genetic", "biometric"}
    if not any(d in sc for d in c.data_categories):
        return True
    return c.art9_condition not in ("", "none")


def _consent_valid(c: ClientProfile) -> bool:
    return c.consent_valid


def _purpose_match(c: ClientProfile) -> bool:
    return c.purpose_id not in ("", "none")


def _feature_minimized(c: ClientProfile) -> bool:
    return set(c.declared_features).issubset(set(c.approved_features))


def _retention_ok(c: ClientProfile) -> bool:
    return c.retention_ok


def _dpia_ok(c: ClientProfile) -> bool:
    return c.dpia_done


def _epsilon_ok(c: ClientProfile) -> bool:
    return c.epsilon_remaining > 0.0


def _transfer_ok(c: ClientProfile) -> bool:
    from kavp.gdpr import transfer_admissible
    return transfer_admissible(c.jurisdiction, "EU", c.transfer_mechanism) or c.jurisdiction == "EU"


def _processor_in_scope(c: ClientProfile) -> bool:
    return len(c.processor_scope) > 0


def build_gdpr_graph(version: int = 1) -> PolicyGraph:
    g = PolicyGraph(version=version)

    def clause(nid, article, aw, constraints, priority=1.0):
        g.add_node(Node(
            nid=nid, ntype=NodeType.CLAUSE, label=f"GDPR Art.{article}",
            article=article, priority=priority, version=version,
            attrs={"applies_when": aw, "constraints": constraints},
        ))

    clause("C5a", "5(1)(a)", {"domain": [], "jurisdiction": [], "data_category": []},
           [{"key": "legal_basis", "fn": _has_legal_basis, "w": 2.0, "desc": "declared lawful basis"}], 2.0)
    clause("C5b", "5(1)(b)", {}, [{"key": "purpose", "fn": _purpose_match, "w": 1.5}], 1.5)
    clause("C5c", "5(1)(c)", {}, [{"key": "minimization", "fn": _feature_minimized, "w": 1.0}], 1.0)
    clause("C5e", "5(1)(e)", {}, [{"key": "retention", "fn": _retention_ok, "w": 1.0}], 1.0)
    clause("C6", "6", {}, [{"key": "legal_basis", "fn": _has_legal_basis, "w": 2.0}], 2.0)
    clause("C7", "7", {}, [{"key": "consent", "fn": _consent_valid, "w": 2.0}], 2.0)
    clause("C9", "9", {"data_category": ["health", "genetic", "biometric"]},
           [{"key": "art9_condition", "fn": _has_art9_condition, "w": 3.0}], 3.0)
    clause("C25", "25", {}, [{"key": "dp_budget", "fn": _epsilon_ok, "w": 1.0}], 1.0)
    clause("C32", "32", {}, [{"key": "processor_scope", "fn": _processor_in_scope, "w": 1.0}], 1.0)
    clause("C35", "35", {}, [{"key": "dpia", "fn": _dpia_ok, "w": 1.0}], 1.0)
    clause("Ct", "44-49", {}, [{"key": "transfer", "fn": _transfer_ok, "w": 2.5}], 2.5)

    g.add_node(Node(nid="O_art9", ntype=NodeType.OBLIGATION, label="require Art.9(2) condition", article="9"))
    g.add_node(Node(nid="P_xfer", ntype=NodeType.PROHIBITION, label="prohibit transfer without mechanism", article="44-49"))
    g.add_node(Node(nid="E_consent", ntype=NodeType.EXCEPTION, label="explicit-consent exception", article="9"))
    g.add_edge(Edge("C9", "O_art9", EdgeType.REQUIRES))
    g.add_edge(Edge("Ct", "P_xfer", EdgeType.PROHIBITS))
    g.add_edge(Edge("E_consent", "P_xfer", EdgeType.EXCEPTS))
    return g


def build_org_override_graph(version: int = 1) -> PolicyGraph:
    g = build_gdpr_graph(version)
    g.add_node(Node(nid="ORG07", ntype=NodeType.PERMISSION,
                    label="ORG_POLICY_07 permit special-cat w/o 9(2)", article="ORG",
                    priority=0.5, version=version))
    g.add_edge(Edge("O_art9", "ORG07", EdgeType.SUPERIOR))
    return g
