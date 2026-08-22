"""KAVP-GDPR: GDPR typed policy graph with constraint propagation,
defeasible conflict resolution, evidence integrity, and transfer admissibility.

Faithful extension of the KAVP-PGC substrate:
    G = (V, E, tau_V, tau_E, rho, lambda, preceq, nu)
    Satisfies(n_i, c) in {0,1}
    Compliance(n_i, C) = prod_c Satisfies(n_i, c)
    Cost(n_i) = sum_c w_c (1 - Satisfies(n_i, c))
    F(n_i) = 1 iff Compliance >= tau and Cost <= kappa_max
"""
from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class NodeType(str, Enum):
    CLAUSE = "clause"
    OBLIGATION = "obligation"
    PERMISSION = "permission"
    PROHIBITION = "prohibition"
    EXCEPTION = "exception"
    ENTITY = "entity"
    CONDITION = "condition"
    CONTROL = "control"
    JURISDICTION = "jurisdiction"
    PURPOSE = "purpose"
    CONSENT = "consent"
    TRANSFER = "transfer"


class EdgeType(str, Enum):
    REQUIRES = "requires"
    PROHIBITS = "prohibits"
    IMPLIES = "implies"
    APPLIES_TO = "appliesTo"
    EXCEPTS = "excepts"
    GOVERNS = "governs"
    PRECEDES = "precedes"
    SUPERIOR = "superior"
    APPLIES_IN = "appliesIn"


class Modality(str, Enum):
    OBLIGATION = "obligation"
    PERMISSION = "permission"
    PROHIBITION = "prohibition"


@dataclass
class Node:
    nid: str
    ntype: NodeType
    label: str
    article: str = ""
    priority: float = 1.0
    version: int = 1
    effective_from: str = ""
    expiry: str = ""
    attrs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    src: str
    dst: str
    etype: EdgeType
    weight: float = 1.0


@dataclass
class ClientProfile:
    cid: str
    jurisdiction: str
    region: str
    domain: str
    data_categories: List[str]
    legal_basis: str
    art9_condition: str
    consent_valid: bool
    transfer_mechanism: str
    epsilon_remaining: float
    purpose_id: str
    declared_features: List[str]
    approved_features: List[str]
    retention_ok: bool
    dpia_done: bool
    is_controller: bool
    processor_scope: List[str]
    truth_eligible: bool = True


@dataclass
class Decision:
    decision: str
    cid: str
    round: int
    purpose: str
    jurisdiction: str
    applicable: List[str]
    controls: List[str]
    violated: List[str]
    defeated: List[Tuple[str, str]]
    human_review: bool
    policy_version: int
    evidence_ids: List[str]
    explanation_id: str
    timestamp: float
    transfer_admissible: bool
    consent_state: str


class PolicyGraph:
    def __init__(self, version: int = 1):
        self.version = version
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.out: Dict[str, List[Edge]] = {}
        self.inn: Dict[str, List[Edge]] = {}

    def add_node(self, n: Node):
        self.nodes[n.nid] = n
        self.out.setdefault(n.nid, [])
        self.inn.setdefault(n.nid, [])

    def add_edge(self, e: Edge):
        self.edges.append(e)
        self.out.setdefault(e.src, []).append(e)
        self.inn.setdefault(e.dst, []).append(e)

    def descendants(self, nid: str, etype: EdgeType) -> List[str]:
        return [e.dst for e in self.out.get(nid, []) if e.etype == etype]

    def ancestors(self, nid: str, etype: EdgeType) -> List[str]:
        return [e.src for e in self.inn.get(nid, []) if e.etype == etype]

    def applicable_constraints(self, c: ClientProfile) -> List["Constraint"]:
        out: List[Constraint] = []
        for nid, n in self.nodes.items():
            if n.ntype != NodeType.CLAUSE:
                continue
            if not _applies_when(n, c):
                continue
            for con in _extract_constraints(n):
                out.append(con)
        return out


@dataclass
class Constraint:
    cid: str
    weight: float
    article: str
    predicate: Callable[[ClientProfile], bool]
    desc: str

    def satisfies(self, c: ClientProfile) -> int:
        return 1 if self.predicate(c) else 0


def _applies_when(n: Node, c: ClientProfile) -> bool:
    aw = n.attrs.get("applies_when", {})
    if "jurisdiction" in aw and aw["jurisdiction"] and c.jurisdiction not in aw["jurisdiction"]:
        return False
    if "domain" in aw and aw["domain"] and c.domain not in aw["domain"]:
        return False
    if "data_category" in aw and aw["data_category"]:
        if not any(dc in aw["data_category"] for dc in c.data_categories):
            return False
    return True


def _extract_constraints(n: Node) -> List[Constraint]:
    cons: List[Constraint] = []
    art = n.article or n.label
    for spec in n.attrs.get("constraints", []):
        cons.append(Constraint(
            cid=f"{n.nid}:{spec['key']}",
            weight=float(spec.get("w", 1.0)),
            article=art,
            predicate=spec["fn"],
            desc=spec.get("desc", spec["key"]),
        ))
    return cons


def satisfies(c: ClientProfile, con: Constraint) -> int:
    return con.satisfies(c)


def compliance(c: ClientProfile, C: List[Constraint]) -> float:
    prod = 1.0
    for con in C:
        prod *= satisfies(c, con)
    return prod


def cost(c: ClientProfile, C: List[Constraint]) -> float:
    return sum(con.weight * (1 - satisfies(c, con)) for con in C)


def feasibility(c: ClientProfile, C: List[Constraint], tau: float, kappa_max: float) -> int:
    return 1 if (compliance(c, C) >= tau and cost(c, C) <= kappa_max) else 0


@dataclass
class Rule:
    rid: str
    modality: Modality
    target: str
    source: str
    precedence: float
    version: int = 1


class DefeasibleResolver:
    def __init__(self, graph: PolicyGraph):
        self.graph = graph
        self.superiority: Set[Tuple[str, str]] = set()
        for e in graph.edges:
            if e.etype == EdgeType.SUPERIOR:
                self.superiority.add((e.src, e.dst))

    def _conflicts(self, a: Rule, b: Rule) -> bool:
        if a.target != b.target:
            return False
        opposites = {
            (Modality.OBLIGATION, Modality.PROHIBITION),
            (Modality.PROHIBITION, Modality.OBLIGATION),
            (Modality.PERMISSION, Modality.PROHIBITION),
            (Modality.PROHIBITION, Modality.PERMISSION),
        }
        return (a.modality, b.modality) in opposites

    def _defeats(self, a: Rule, b: Rule) -> bool:
        if not self._conflicts(a, b):
            return False
        if (a.rid, b.rid) in self.superiority:
            return True
        if a.precedence > b.precedence:
            return True
        if a.precedence == b.precedence and a.version > b.version:
            return True
        return False

    def resolve(self, rules: List[Rule]) -> Tuple[List[Rule], List[Tuple[str, str]]]:
        undefeated: List[Rule] = []
        defeats: List[Tuple[str, str]] = []
        for r in rules:
            beaten = False
            for s in rules:
                if s.rid == r.rid:
                    continue
                if self._defeats(s, r):
                    defeats.append((s.rid, r.rid))
                    beaten = True
                    break
            if not beaten:
                undefeated.append(r)
        return undefeated, defeats


CONTROL_TABLE: Dict[str, Dict[str, Any]] = {
    "5(1)(a)": {"control": "legal_basis_check", "module": "M6,M7", "evidence": "lawful_basis_id"},
    "5(1)(b)": {"control": "purpose_binding", "module": "M6,M9", "evidence": "purpose_id"},
    "5(1)(c)": {"control": "feature_minimization", "module": "M6,M8", "evidence": "feature_mask_hash"},
    "5(1)(e)": {"control": "retention_policy", "module": "M6", "evidence": "retention_ref"},
    "5(1)(f)": {"control": "secure_aggregation", "module": "M8", "evidence": "transport_evidence"},
    "5(2)": {"control": "evidence_record", "module": "M11", "evidence": "decision_hash"},
    "6": {"control": "lawful_basis_check", "module": "M7", "evidence": "basis_id"},
    "7": {"control": "consent_state_check", "module": "M7", "evidence": "consent_digest"},
    "9": {"control": "art9_condition_check", "module": "M7", "evidence": "art9_condition_id"},
    "17": {"control": "federated_unlearning", "module": "M10", "evidence": "unlearning_cert"},
    "21": {"control": "objection_unlearning", "module": "M10", "evidence": "optout_event"},
    "22": {"control": "human_review", "module": "M13", "evidence": "review_ticket"},
    "25": {"control": "dp_plus_secagg_bydefault", "module": "M6,M8", "evidence": "design_manifest"},
    "30": {"control": "ropa_auto", "module": "M11", "evidence": "ropa_fragment"},
    "32": {"control": "security_of_processing", "module": "M8", "evidence": "security_manifest"},
    "35": {"control": "dpia_attach", "module": "M7", "evidence": "dpia_ref"},
    "44-49": {"control": "transfer_mechanism_resolver", "module": "M7", "evidence": "transfer_decision"},
}


def compile_controls(articles: List[str]) -> List[str]:
    out: List[str] = []
    for a in articles:
        if a in CONTROL_TABLE:
            out.append(CONTROL_TABLE[a]["control"])
    return list(dict.fromkeys(out))


def required_evidence(articles: List[str]) -> List[str]:
    out: List[str] = []
    for a in articles:
        if a in CONTROL_TABLE:
            out.append(CONTROL_TABLE[a]["evidence"])
    return list(dict.fromkeys(out))


class EvidenceStore:
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.counter = 0
        self.last_hash = "0" * 64

    def _h(self, payload: str) -> str:
        return hashlib.sha256(payload.encode()).hexdigest()

    def record(self, decision: Decision, required: List[str], generated: List[str]) -> Tuple[str, str]:
        self.counter += 1
        evid = f"EVT-{self.counter:06d}"
        payload = f"{decision.cid}|{decision.round}|{decision.decision}|{','.join(generated)}|{self.last_hash}"
        h = self._h(payload)
        rec = {
            "evidence_id": evid,
            "decision": decision.decision,
            "cid": decision.cid,
            "round": decision.round,
            "required": required,
            "generated": generated,
            "complete": set(required).issubset(set(generated)),
            "prev_hash": self.last_hash,
            "hash": h,
        }
        self.events.append(rec)
        self.last_hash = h
        return evid, h

    def audit_completeness(self) -> float:
        if not self.events:
            return 1.0
        return sum(1 for e in self.events if e["complete"]) / len(self.events)

    def integrity_ok(self) -> bool:
        prev = "0" * 64
        for e in self.events:
            payload = f"{e['cid']}|{e['round']}|{e['decision']}|{','.join(e['generated'])}|{prev}"
            if self._h(payload) != e["hash"]:
                return False
            prev = e["hash"]
        return True


class VersionHandler:
    def __init__(self, graph: PolicyGraph):
        self.graph = graph

    def migrate(self, new_graph: PolicyGraph, active_decisions: List[Decision]) -> Dict[str, Any]:
        old_obls = {n.nid for n in self.graph.nodes.values() if n.ntype == NodeType.OBLIGATION}
        new_obls = {n.nid for n in new_graph.nodes.values() if n.ntype == NodeType.OBLIGATION}
        dropped = old_obls - new_obls
        flagged: List[str] = []
        for d in active_decisions:
            if dropped and not getattr(d, "_migrated", False):
                flagged.append(d.cid)
        from_version = self.graph.version
        self.graph = new_graph
        return {"from": from_version, "to": new_graph.version,
                "dropped_obligations": list(dropped), "flagged": flagged}


def needs_review(decision: Decision, exception_evidence_complete: bool,
                 art22: bool = False, org_override: bool = False) -> bool:
    return art22 or (not exception_evidence_complete) or org_override or decision.decision == "conditional"


class UnlearningManager:
    def __init__(self, model_apply_grad, influence_norm):
        self.apply_grad = model_apply_grad
        self.influence_norm = influence_norm

    def unlearn(self, footprint_grad: Dict[str, Any], init_footprint: float,
                target_rho: float = 0.9, lr: float = 1e-2, max_steps: int = 50) -> Tuple[float, int]:
        steps = 0
        for _ in range(max_steps):
            self.apply_grad(footprint_grad, lr)
            steps += 1
            cur = self.influence_norm()
            if cur <= 0:
                break
            rho = 1.0 - cur / init_footprint if init_footprint > 0 else 1.0
            if rho >= target_rho:
                break
        return rho, steps


ADEQUACY_JURISDICTIONS = {"EU", "EEA", "UK", "CH", "JP"}


def transfer_admissible(j_src: str, j_dst: str, mechanism: str) -> bool:
    if j_src == j_dst:
        return True
    if mechanism == "adequacy" and j_dst in ADEQUACY_JURISDICTIONS:
        return True
    if mechanism == "scc":
        return True
    if mechanism == "derogation":
        return True
    return False
