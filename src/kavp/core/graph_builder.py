import networkx as nx
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime
from kavp.core.parser import ParsedPolicy, ParsedEntity, ParsedAction, ParsedConstraint


class GraphNode(BaseModel):
    node_id: str
    label: str
    node_type: str
    properties: Dict = {}
    policy_sources: List[str] = []


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: str
    label: str
    properties: Dict = {}


class PolicyGraph(BaseModel):
    graph_id: str
    created_at: datetime = datetime.now()
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []

    class Config:
        arbitrary_types_allowed = True


NODE_COLORS = {
    "policy": "#3B82F6",
    "entity": "#10B981",
    "constraint": "#EF4444",
    "action": "#F59E0B",
    "jurisdiction": "#8B5CF6"
}


class GraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_metadata: Dict[str, Dict] = {}
        self.graphs: Dict[str, PolicyGraph] = {}

    def build_graph(self, parsed_policies: List[ParsedPolicy], graph_id: str = "main") -> PolicyGraph:
        self.graph = nx.DiGraph()
        self.node_metadata = {}

        for policy in parsed_policies:
            policy_node_id = f"POL_{policy.policy_id}"
            self._add_policy_node(policy_node_id, policy)

            for entity in policy.entities:
                entity_node_id = f"ENT_{entity.name.replace(' ', '_')}"
                self._add_entity_node(entity_node_id, entity, policy.policy_id)
                self.graph.add_edge(policy_node_id, entity_node_id,
                                   edge_type="appliesTo", label="appliesTo")

            for action in policy.actions:
                action_node_id = f"ACT_{action.verb}"
                self._add_action_node(action_node_id, action, policy.policy_id)
                self.graph.add_edge(policy_node_id, action_node_id,
                                   edge_type="governs", label="governs")

                if action.target:
                    target_node_id = f"ENT_{action.target.replace(' ', '_')}"
                    self.graph.add_edge(action_node_id, target_node_id,
                                       edge_type="targets", label="targets")

            for constraint in policy.constraints:
                constraint_node_id = f"CON_{constraint.attribute}_{constraint.value}"
                self._add_constraint_node(constraint_node_id, constraint, policy.policy_id)
                self.graph.add_edge(policy_node_id, constraint_node_id,
                                   edge_type="requires", label="requires")

                if constraint.jurisdiction:
                    jur_node_id = f"JUR_{constraint.jurisdiction}"
                    self._add_jurisdiction_node(jur_node_id, constraint.jurisdiction)
                    self.graph.add_edge(constraint_node_id, jur_node_id,
                                       edge_type="jurisdiction", label="jurisdiction")

            for prohibition in policy.prohibitions:
                prohibit_node_id = f"PRO_{prohibition}"
                self._add_prohibition_node(prohibit_node_id, prohibition, policy.policy_id)
                self.graph.add_edge(policy_node_id, prohibit_node_id,
                                   edge_type="prohibits", label="prohibits")

            if policy.jurisdiction:
                jur_node_id = f"JUR_{policy.jurisdiction}"
                self._add_jurisdiction_node(jur_node_id, policy.jurisdiction)
                self.graph.add_edge(policy_node_id, jur_node_id,
                                   edge_type="appliesIn", label="appliesIn")

            for tag in policy.compliance_tags:
                tag_node_id = f"CMP_{tag}"
                self._add_compliance_node(tag_node_id, tag, policy.policy_id)
                self.graph.add_edge(policy_node_id, tag_node_id,
                                   edge_type="requiresCompliance", label="requiresCompliance")

        self._create_inferred_edges()

        graph = PolicyGraph(
            graph_id=graph_id,
            nodes=[self._create_node_from_id(n) for n in self.graph.nodes()],
            edges=[self._create_edge_from_data(u, v, self.graph.edges[u, v])
                   for u, v in self.graph.edges()]
        )
        self.graphs[graph_id] = graph
        return graph

    def _add_policy_node(self, node_id: str, policy: ParsedPolicy):
        self.graph.add_node(node_id,
                           label=policy.policy_id,
                           node_type="policy",
                           color=NODE_COLORS["policy"])
        self.node_metadata[node_id] = {
            "node_type": "policy",
            "original_text": policy.original_text,
            "policy_id": policy.policy_id,
            "compliance_tags": policy.compliance_tags,
            "privacy_rules": policy.privacy_rules
        }

    def _add_entity_node(self, node_id: str, entity: ParsedEntity, policy_id: str):
        if node_id not in self.graph:
            self.graph.add_node(node_id,
                               label=entity.name,
                               node_type="entity",
                               color=NODE_COLORS["entity"])
            self.node_metadata[node_id] = {
                "node_type": "entity",
                "entity_type": entity.type,
                "roles": entity.roles
            }
        else:
            if policy_id not in self.node_metadata[node_id].get("policy_sources", []):
                self.node_metadata[node_id]["policy_sources"] = \
                    self.node_metadata[node_id].get("policy_sources", []) + [policy_id]

    def _add_action_node(self, node_id: str, action: ParsedAction, policy_id: str):
        if node_id not in self.graph:
            self.graph.add_node(node_id,
                               label=action.verb,
                               node_type="action",
                               color=NODE_COLORS["action"])
            self.node_metadata[node_id] = {
                "node_type": "action",
                "modality": action.modality,
                "target": action.target
            }

    def _add_constraint_node(self, node_id: str, constraint: ParsedConstraint, policy_id: str):
        if node_id not in self.graph:
            label = f"{constraint.attribute} {constraint.operator} {constraint.value}"
            self.graph.add_node(node_id,
                               label=label,
                               node_type="constraint",
                               color=NODE_COLORS["constraint"])
            self.node_metadata[node_id] = {
                "node_type": "constraint",
                "attribute": constraint.attribute,
                "operator": constraint.operator,
                "value": constraint.value,
                "jurisdiction": constraint.jurisdiction
            }

    def _add_jurisdiction_node(self, node_id: str, jurisdiction: str):
        if node_id not in self.graph:
            self.graph.add_node(node_id,
                               label=jurisdiction,
                               node_type="jurisdiction",
                               color=NODE_COLORS["jurisdiction"])
            self.node_metadata[node_id] = {
                "node_type": "jurisdiction",
                "name": jurisdiction
            }

    def _add_prohibition_node(self, node_id: str, prohibition: str, policy_id: str):
        if node_id not in self.graph:
            self.graph.add_node(node_id,
                               label=prohibition,
                               node_type="prohibition",
                               color="#DC2626")
            self.node_metadata[node_id] = {
                "node_type": "prohibition",
                "description": prohibition
            }

    def _add_compliance_node(self, node_id: str, tag: str, policy_id: str):
        if node_id not in self.graph:
            self.graph.add_node(node_id,
                               label=tag,
                               node_type="compliance",
                               color="#6366F1")
            self.node_metadata[node_id] = {
                "node_type": "compliance",
                "framework": tag
            }

    def _create_inferred_edges(self):
        for u, v, data in self.graph.edges(data=True):
            if data.get("edge_type") == "appliesTo":
                if self.node_metadata.get(v, {}).get("node_type") == "entity":
                    entity_type = self.node_metadata[v].get("entity_type")
                    if entity_type == "region":
                        self.graph.add_edge(v, u, edge_type="governs", label="governs")

    def _create_node_from_id(self, node_id: str) -> GraphNode:
        attrs = self.graph.nodes[node_id]
        meta = self.node_metadata.get(node_id, {})
        return GraphNode(
            node_id=node_id,
            label=attrs.get("label", node_id),
            node_type=attrs.get("node_type", "unknown"),
            properties=meta,
            policy_sources=[]
        )

    def _create_edge_from_data(self, source: str, target: str, edge_data: dict) -> GraphEdge:
        return GraphEdge(
            source=source,
            target=target,
            edge_type=edge_data.get("edge_type", "unknown"),
            label=edge_data.get("label", "related"),
            properties={}
        )

    def get_graph(self, graph_id: str = "main") -> nx.DiGraph:
        return self.graph

    def get_node_metadata(self, node_id: str) -> Dict:
        return self.node_metadata.get(node_id, {})

    def get_nodes_by_type(self, node_type: str) -> List[str]:
        return [n for n, attrs in self.graph.nodes(data=True)
                if attrs.get("node_type") == node_type]

    def get_subgraph(self, node_ids: List[str]) -> nx.DiGraph:
        return self.graph.subgraph(node_ids).copy()

    def get_policy_trace(self, entity_node_id: str) -> List[Tuple[str, str]]:
        trace = []
        if entity_node_id in self.graph:
            predecessors = list(self.graph.predecessors(entity_node_id))
            for pred in predecessors:
                edge_data = self.graph.edges[pred, entity_node_id]
                trace.append((pred, edge_data.get("label", "related")))
                trace.extend(self.get_policy_trace(pred))
        return trace
