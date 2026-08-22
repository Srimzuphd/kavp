from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class LogLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    SUCCESS = "success"


class AuditEvent(BaseModel):
    event_id: str
    timestamp: datetime
    event_type: str
    category: str
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    policy_source: Optional[str] = None
    decision: str
    details: str
    severity: LogLevel = LogLevel.INFO


class AuditLogger:
    def __init__(self):
        self.events: List[AuditEvent] = []
        self.event_counter = 0
        self.log_file_path: Optional[str] = None

    def log(self, event_type: str, category: str, decision: str, details: str,
            node_id: Optional[str] = None, node_name: Optional[str] = None,
            policy_source: Optional[str] = None, severity: LogLevel = LogLevel.INFO) -> AuditEvent:

        self.event_counter += 1
        event = AuditEvent(
            event_id=f"AUD-{self.event_counter:06d}",
            timestamp=datetime.now(),
            event_type=event_type,
            category=category,
            node_id=node_id,
            node_name=node_name,
            policy_source=policy_source,
            decision=decision,
            details=details,
            severity=severity
        )

        self.events.append(event)
        return event

    def log_policy_loaded(self, policy_id: str, text: str):
        return self.log(
            event_type="policy_loaded",
            category="policy_ingestion",
            decision="loaded",
            details=f"Policy loaded: {text[:50]}...",
            policy_source=policy_id
        )

    def log_policy_parsed(self, policy_id: str, entities_count: int, constraints_count: int):
        return self.log(
            event_type="policy_parsed",
            category="policy_parsing",
            decision="parsed",
            details=f"Extracted {entities_count} entities, {constraints_count} constraints",
            policy_source=policy_id
        )

    def log_graph_built(self, node_count: int, edge_count: int):
        return self.log(
            event_type="graph_built",
            category="graph_construction",
            decision="completed",
            details=f"Policy graph constructed with {node_count} nodes and {edge_count} edges"
        )

    def log_constraint_evaluated(self, node_id: str, node_name: str,
                                  policy_id: str, passed: bool, reason: str):
        return self.log(
            event_type="constraint_evaluated",
            category="constraint_propagation",
            decision="passed" if passed else "failed",
            details=reason,
            node_id=node_id,
            node_name=node_name,
            policy_source=policy_id,
            severity=LogLevel.WARNING if not passed else LogLevel.INFO
        )

    def log_node_eligibility(self, node_id: str, node_name: str, eligible: bool,
                             compliance_score: float, reason: str):
        severity = LogLevel.SUCCESS if eligible else LogLevel.ERROR
        return self.log(
            event_type="node_evaluated",
            category="orchestration",
            decision="eligible" if eligible else "blocked",
            details=f"{reason} (Score: {compliance_score:.1f})",
            node_id=node_id,
            node_name=node_name,
            severity=severity
        )

    def log_task_created(self, task_id: str, selected_count: int, blocked_count: int):
        return self.log(
            event_type="task_created",
            category="orchestration",
            decision="created",
            details=f"Task {task_id}: {selected_count} eligible, {blocked_count} blocked",
            severity=LogLevel.INFO
        )

    def log_violation(self, node_id: str, node_name: str, violation: str,
                      policy_source: str, severity: LogLevel = LogLevel.CRITICAL):
        return self.log(
            event_type="violation_detected",
            category="compliance",
            decision="violation",
            details=violation,
            node_id=node_id,
            node_name=node_name,
            policy_source=policy_source,
            severity=severity
        )

    def get_events(self, category: Optional[str] = None,
                   node_id: Optional[str] = None,
                   limit: Optional[int] = None) -> List[AuditEvent]:

        filtered = self.events

        if category:
            filtered = [e for e in filtered if e.category == category]

        if node_id:
            filtered = [e for e in filtered if e.node_id == node_id]

        if limit:
            filtered = filtered[-limit:]

        return filtered

    def get_violations(self) -> List[AuditEvent]:
        return [e for e in self.events if e.severity in [LogLevel.ERROR, LogLevel.CRITICAL]]

    def get_node_history(self, node_id: str) -> List[AuditEvent]:
        return [e for e in self.events if e.node_id == node_id]

    def clear(self):
        self.events = []
        self.event_counter = 0

    def export_logs(self) -> List[Dict]:
        return [e.model_dump() for e in self.events]

    def get_summary(self) -> Dict:
        return {
            "total_events": len(self.events),
            "by_category": self._count_by_category(),
            "by_severity": self._count_by_severity(),
            "by_node": self._count_by_node(),
            "violations_count": len(self.get_violations())
        }

    def _count_by_category(self) -> Dict[str, int]:
        counts = {}
        for event in self.events:
            counts[event.category] = counts.get(event.category, 0) + 1
        return counts

    def _count_by_severity(self) -> Dict[str, int]:
        counts = {}
        for event in self.events:
            counts[event.severity.value] = counts.get(event.severity.value, 0) + 1
        return counts

    def _count_by_node(self) -> Dict[str, int]:
        counts = {}
        for event in self.events:
            if event.node_id:
                counts[event.node_id] = counts.get(event.node_id, 0) + 1
        return counts

    def get_timeline(self, limit: int = 20) -> List[Tuple[datetime, str, str, str]]:
        return [(e.timestamp, e.event_type, e.decision, e.details) for e in self.events[-limit:]]
