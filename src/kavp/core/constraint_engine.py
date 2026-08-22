from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime
from kavp.core.parser import ParsedPolicy
from kavp.core.graph_builder import GraphBuilder, GraphNode


class NodeProfile(BaseModel):
    node_id: str
    name: str
    region: str
    domain: str
    compliance_tags: List[str]
    privacy_budget: float = 10.0
    epsilon: float = 5.0
    is_active: bool = True
    data_classification: str = "sensitive"


class ConstraintResult(BaseModel):
    node_id: str
    policy_id: str
    constraint_type: str
    passed: bool
    reason: str
    severity: str = "info"


class PropagationResult(BaseModel):
    node_id: str
    node_name: str
    eligible: bool
    compliance_score: float
    constraints_applied: List[str]
    violations: List[str]
    warnings: List[str]
    decision_reason: str
    timestamp: datetime = datetime.now()


class ConstraintPropagation:
    def __init__(self, graph_builder: GraphBuilder):
        self.graph_builder = graph_builder
        self.results: Dict[str, PropagationResult] = {}

    def evaluate_node(self, node: NodeProfile, policies: List[ParsedPolicy]) -> PropagationResult:
        violations = []
        warnings = []
        constraints_applied = []
        passed_constraints = []

        for policy in policies:
            constraint_results = self._evaluate_policy_constraints(node, policy)
            for result in constraint_results:
                constraints_applied.append(f"{policy.policy_id}:{result.constraint_type}")
                if result.passed:
                    passed_constraints.append(result.constraint_type)
                else:
                    if result.severity == "critical":
                        violations.append(result.reason)
                    else:
                        warnings.append(result.reason)

        compliance_score = self._calculate_compliance_score(
            len(policies), len(violations), len(warnings)
        )

        eligible = len(violations) == 0

        decision_reason = self._generate_decision_reason(
            eligible, violations, warnings, passed_constraints
        )

        result = PropagationResult(
            node_id=node.node_id,
            node_name=node.name,
            eligible=eligible,
            compliance_score=compliance_score,
            constraints_applied=constraints_applied,
            violations=violations,
            warnings=warnings,
            decision_reason=decision_reason
        )

        self.results[node.node_id] = result
        return result

    def _evaluate_policy_constraints(self, node: NodeProfile, policy: ParsedPolicy) -> List[ConstraintResult]:
        results = []

        for constraint in policy.constraints:
            if constraint.attribute == "region":
                if constraint.operator == "not_in":
                    restricted_region = constraint.value.lower()
                    node_region = node.region.lower()

                    if "eu" in restricted_region and "eu" in node_region:
                        results.append(ConstraintResult(
                            node_id=node.node_id,
                            policy_id=policy.policy_id,
                            constraint_type="region_check",
                            passed=True,
                            reason=f"Node region '{node.region}' complies with {constraint.value} restriction (data stays within EU)",
                            severity="info"
                        ))
                    elif "national borders" in restricted_region:
                        if node_region in ["eu", "us", "india", "uk"]:
                            results.append(ConstraintResult(
                                node_id=node.node_id,
                                policy_id=policy.policy_id,
                                constraint_type="region_check",
                                passed=True,
                                reason=f"Node region '{node.region}' - data remains within national boundaries",
                                severity="info"
                            ))
                        else:
                            results.append(ConstraintResult(
                                node_id=node.node_id,
                                policy_id=policy.policy_id,
                                constraint_type="region_violation",
                                passed=False,
                                reason=f"Node region '{node.region}' violates policy: data cannot leave {constraint.value}",
                                severity="critical"
                            ))
                    elif "eu" not in node_region and "eu" in restricted_region:
                        results.append(ConstraintResult(
                            node_id=node.node_id,
                            policy_id=policy.policy_id,
                            constraint_type="region_violation",
                            passed=False,
                            reason=f"Node region '{node.region}' violates policy: data cannot leave {constraint.value}",
                            severity="critical"
                        ))
                    else:
                        results.append(ConstraintResult(
                            node_id=node.node_id,
                            policy_id=policy.policy_id,
                            constraint_type="region_check",
                            passed=True,
                            reason=f"Node region '{node.region}' complies with {constraint.value} restriction",
                            severity="info"
                        ))

            elif constraint.attribute == "epsilon":
                threshold = float(constraint.value)
                if constraint.operator == "<":
                    if node.epsilon >= threshold:
                        results.append(ConstraintResult(
                            node_id=node.node_id,
                            policy_id=policy.policy_id,
                            constraint_type="epsilon_violation",
                            passed=False,
                            reason=f"Epsilon {node.epsilon} exceeds threshold {threshold}",
                            severity="critical"
                        ))
                    else:
                        results.append(ConstraintResult(
                            node_id=node.node_id,
                            policy_id=policy.policy_id,
                            constraint_type="epsilon_check",
                            passed=True,
                            reason=f"Epsilon {node.epsilon} within threshold {threshold}",
                            severity="info"
                        ))

            elif constraint.attribute == "privacy_budget":
                threshold = float(constraint.value)
                if constraint.operator == "<":
                    if node.privacy_budget >= threshold:
                        results.append(ConstraintResult(
                            node_id=node.node_id,
                            policy_id=policy.policy_id,
                            constraint_type="budget_violation",
                            passed=False,
                            reason=f"Privacy budget {node.privacy_budget} exceeds threshold {threshold}",
                            severity="critical"
                        ))

        policy_has_required_compliance = set(policy.compliance_tags)

        if policy_has_required_compliance:
            node_compliance = set(node.compliance_tags)
            has_overlap = bool(node_compliance.intersection(policy_has_required_compliance))

            if not has_overlap:
                missing = policy_has_required_compliance - node_compliance
                results.append(ConstraintResult(
                    node_id=node.node_id,
                    policy_id=policy.policy_id,
                    constraint_type="compliance_tag",
                    passed=False,
                    reason=f"Node missing required compliance for this policy: {', '.join(missing)}",
                    severity="critical"
                ))
            else:
                matched = node_compliance.intersection(policy_has_required_compliance)
                results.append(ConstraintResult(
                    node_id=node.node_id,
                    policy_id=policy.policy_id,
                    constraint_type="compliance_tag",
                    passed=True,
                    reason=f"Node has required compliance: {', '.join(matched)}",
                    severity="info"
                ))

        for prohibition in policy.prohibitions:
            if self._check_prohibition_applies(node, prohibition, policy):
                results.append(ConstraintResult(
                    node_id=node.node_id,
                    policy_id=policy.policy_id,
                    constraint_type="prohibition",
                    passed=False,
                    reason=f"Policy prohibits: {prohibition}",
                    severity="critical"
                ))

        return results

    def _check_prohibition_applies(self, node: NodeProfile, prohibition: str, policy: ParsedPolicy) -> bool:
        if "leave" in prohibition or "transfer" in prohibition:
            return True
        return False

    def _calculate_compliance_score(self, total_policies: int, violations: int, warnings: int) -> float:
        if total_policies == 0:
            return 100.0

        base_score = 100.0
        violation_penalty = (violations / total_policies) * 60
        warning_penalty = (warnings / total_policies) * 20

        score = base_score - violation_penalty - warning_penalty
        return max(0.0, min(100.0, score))

    def _generate_decision_reason(self, eligible: bool, violations: List[str],
                                   warnings: List[str], passed: List[str]) -> str:
        if eligible:
            if warnings:
                return f"Eligible with warnings: {'; '.join(warnings[:2])}"
            return "Fully compliant - all policy constraints satisfied"
        else:
            return f"Blocked: {'; '.join(violations[:2])}"

    def evaluate_all_nodes(self, nodes: List[NodeProfile],
                          policies: List[ParsedPolicy]) -> Dict[str, PropagationResult]:
        results = {}
        for node in nodes:
            results[node.node_id] = self.evaluate_node(node, policies)
        return results

    def get_eligible_nodes(self) -> List[str]:
        return [node_id for node_id, result in self.results.items() if result.eligible]

    def get_blocked_nodes(self) -> List[str]:
        return [node_id for node_id, result in self.results.items() if not result.eligible]

    def get_violations_summary(self) -> Dict[str, List[str]]:
        summary = {}
        for node_id, result in self.results.items():
            if result.violations:
                summary[node_id] = result.violations
        return summary
