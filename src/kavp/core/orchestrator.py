from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime
from kavp.core.constraint_engine import NodeProfile, PropagationResult
from kavp.core.graph_builder import GraphBuilder


class OrchestrationDecision(BaseModel):
    task_id: str
    selected_nodes: List[str]
    blocked_nodes: List[str]
    rationale: str
    timestamp: datetime = datetime.now()


class FederatedOrchestrator:
    def __init__(self, graph_builder: GraphBuilder):
        self.graph_builder = graph_builder
        self.active_nodes: Dict[str, NodeProfile] = {}
        self.decision_history: List[OrchestrationDecision] = []
        self.current_task_id = 0

    def register_node(self, node: NodeProfile):
        self.active_nodes[node.node_id] = node

    def register_nodes(self, nodes: List[NodeProfile]):
        for node in nodes:
            self.register_node(node)

    def create_task(self, task_name: str, propagation_results: Dict[str, PropagationResult]) -> OrchestrationDecision:
        self.current_task_id += 1
        task_id = f"TASK-{self.current_task_id:04d}"

        eligible_nodes = []
        blocked_nodes = []
        blocked_reasons = {}

        for node_id, result in propagation_results.items():
            if result.eligible:
                eligible_nodes.append(node_id)
            else:
                blocked_nodes.append(node_id)
                blocked_reasons[node_id] = result.decision_reason

        rationale = self._generate_rationale(task_name, eligible_nodes, blocked_nodes, blocked_reasons)

        decision = OrchestrationDecision(
            task_id=task_id,
            selected_nodes=eligible_nodes,
            blocked_nodes=blocked_nodes,
            rationale=rationale
        )

        self.decision_history.append(decision)
        return decision

    def _generate_rationale(self, task_name: str, eligible: List[str],
                            blocked: List[str], reasons: Dict[str, str]) -> str:
        lines = [f"Task: {task_name}"]
        lines.append(f"Selected {len(eligible)} nodes: {', '.join(eligible) if eligible else 'None'}")

        if blocked:
            lines.append(f"Blocked {len(blocked)} nodes:")
            for node_id, reason in reasons.items():
                lines.append(f"  - {node_id}: {reason}")

        return "\n".join(lines)

    def get_node_status(self, node_id: str) -> Dict:
        if node_id not in self.active_nodes:
            return {"status": "unknown"}

        node = self.active_nodes[node_id]
        return {
            "node_id": node_id,
            "name": node.name,
            "region": node.region,
            "domain": node.domain,
            "compliance_tags": node.compliance_tags,
            "is_active": node.is_active,
            "status": "active" if node.is_active else "inactive"
        }

    def get_decision_summary(self) -> Dict:
        if not self.decision_history:
            return {"total_tasks": 0}

        latest = self.decision_history[-1]
        return {
            "total_tasks": len(self.decision_history),
            "latest_task": latest.task_id,
            "selected_count": len(latest.selected_nodes),
            "blocked_count": len(latest.blocked_nodes),
            "total_active_nodes": len(self.active_nodes)
        }

    def get_node_details(self, node_id: str) -> Optional[NodeProfile]:
        return self.active_nodes.get(node_id)

    def update_node_state(self, node_id: str, is_active: bool):
        if node_id in self.active_nodes:
            self.active_nodes[node_id].is_active = is_active

    def get_eligible_nodes_for_task(self, propagation_results: Dict[str, PropagationResult]) -> List[NodeProfile]:
        eligible = []
        for node_id, result in propagation_results.items():
            if result.eligible and node_id in self.active_nodes:
                eligible.append(self.active_nodes[node_id])
        return eligible


class DemoNodeFactory:
    HEALTHCARE_NODES = [
        NodeProfile(node_id="HOSP_A", name="Hospital A (Berlin)", region="EU", domain="healthcare",
                   compliance_tags=["HIPAA", "GDPR"], privacy_budget=1.5, epsilon=1.8),
        NodeProfile(node_id="HOSP_B", name="Hospital B (Boston)", region="US", domain="healthcare",
                   compliance_tags=["HIPAA"], privacy_budget=2.5, epsilon=2.2),
        NodeProfile(node_id="HOSP_C", name="Hospital C (Munich)", region="EU", domain="healthcare",
                   compliance_tags=["HIPAA", "GDPR"], privacy_budget=1.0, epsilon=1.5),
    ]

    FOOD_TECH_NODES = [
        NodeProfile(node_id="FOOD_LAB_D", name="Food Lab D (Mumbai)", region="India", domain="food_safety",
                   compliance_tags=["FSSAI"], privacy_budget=5.0, epsilon=3.0),
        NodeProfile(node_id="FOOD_LAB_E", name="Food Lab E (Delhi)", region="India", domain="food_safety",
                   compliance_tags=["FSSAI"], privacy_budget=4.0, epsilon=2.5),
        NodeProfile(node_id="FOOD_LAB_F", name="Food Lab F (Paris)", region="EU", domain="food_safety",
                   compliance_tags=["HACCP"], privacy_budget=3.0, epsilon=2.0),
    ]

    FINANCE_NODES = [
        NodeProfile(node_id="BANK_G", name="Bank G (Frankfurt)", region="EU", domain="finance",
                   compliance_tags=["GDPR", "PCI"], privacy_budget=1.2, epsilon=1.0),
        NodeProfile(node_id="BANK_H", name="Bank H (London)", region="UK", domain="finance",
                   compliance_tags=["PCI"], privacy_budget=2.0, epsilon=1.5),
        NodeProfile(node_id="BANK_I", name="Bank I (New York)", region="US", domain="finance",
                   compliance_tags=["PCI", "SOX"], privacy_budget=3.0, epsilon=2.0),
    ]

    MIXED_NODES = [
        NodeProfile(node_id="HOSP_A", name="Hospital A (Berlin)", region="EU", domain="healthcare",
                   compliance_tags=["HIPAA", "GDPR"], privacy_budget=1.5, epsilon=1.8),
        NodeProfile(node_id="HOSP_B", name="Hospital B (Boston)", region="US", domain="healthcare",
                   compliance_tags=["HIPAA"], privacy_budget=2.5, epsilon=2.2),
        NodeProfile(node_id="FOOD_LAB_D", name="Food Lab D (Mumbai)", region="India", domain="food_safety",
                   compliance_tags=["FSSAI"], privacy_budget=5.0, epsilon=3.0),
        NodeProfile(node_id="BANK_G", name="Bank G (Frankfurt)", region="EU", domain="finance",
                   compliance_tags=["GDPR", "PCI"], privacy_budget=1.2, epsilon=1.0),
        NodeProfile(node_id="FOOD_LAB_E", name="Food Lab E (Delhi)", region="India", domain="food_safety",
                   compliance_tags=["FSSAI"], privacy_budget=4.0, epsilon=2.5),
    ]

    @staticmethod
    def get_nodes(scenario: str) -> List[NodeProfile]:
        if scenario == "healthcare":
            return DemoNodeFactory.HEALTHCARE_NODES
        elif scenario == "food_tech":
            return DemoNodeFactory.FOOD_TECH_NODES
        elif scenario == "finance":
            return DemoNodeFactory.FINANCE_NODES
        else:
            return DemoNodeFactory.MIXED_NODES
