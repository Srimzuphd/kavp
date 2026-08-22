from typing import Dict, List, Set, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import re


class ParsedEntity(BaseModel):
    name: str
    type: str
    roles: List[str] = Field(default_factory=list)


class ParsedAction(BaseModel):
    verb: str
    target: Optional[str] = None
    modality: str


class ParsedConstraint(BaseModel):
    attribute: str
    operator: str
    value: str | int | float
    jurisdiction: Optional[str] = None


class ParsedPolicy(BaseModel):
    policy_id: str
    original_text: str
    parsed_at: datetime = Field(default_factory=datetime.now)
    entities: List[ParsedEntity] = Field(default_factory=list)
    actions: List[ParsedAction] = Field(default_factory=list)
    constraints: List[ParsedConstraint] = Field(default_factory=list)
    obligations: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    prohibitions: List[str] = Field(default_factory=list)
    jurisdiction: Optional[str] = None
    compliance_tags: List[str] = Field(default_factory=list)
    privacy_rules: List[str] = Field(default_factory=list)


ENTITY_PATTERNS = {
    "data": ["data", "patient data", "medical data", "food safety data", "financial data", "information", "records"],
    "region": ["EU", "US", "India", "UK", "EU region", "national borders", "licensed institutions"],
    "organization": ["hospital", "bank", "lab", "facility", "institution", "third party", "node"],
    "person": ["patient", "customer", "user", "party", "consent"],
    "system": ["system", "cold chain", "database", "network"]
}

ACTION_VERBS = {
    "transfer": ["transfer", "leave", "move", "share", "transmit"],
    "access": ["access", "view", "retrieve", "use"],
    "process": ["process", "analyze", "compute", "train"],
    "store": ["store", "keep", "maintain", "retain"]
}

CONSTRAINT_KEYWORDS = {
    "epsilon": r"epsilon\s*(?:must|should|remain|be)\s*(?:below|greater than|equal to)?\s*([\d.]+)",
    "budget": r"budget\s*(?:must|should|remain)\s*(?:below|under|above)\s*([\d.]+)",
    "region": r"(?:cannot|may not|must not)\s+(?:leave|transfer|move)\s+([^.]+)",
    "consent": r"require[s]?\s+(?:explicit\s+)?(?:patient|customer|user|all\s+)?consent",
    "compliance": r"(?:HIPAA|GDPR|FSSAI|PCI)\s*(?:compliance|compliant)",
    "localization": r"(?:must|should)\s+(?:remain|stay|be)\s+within",
    "authorization": r"authorize[dz]?[e]?d?\s+(?:third\s+)?party",
}


class PolicyParser:
    def __init__(self):
        self.parsed_policies: List[ParsedPolicy] = []

    def parse(self, policy_id: str, text: str) -> ParsedPolicy:
        entities = self._extract_entities(text)
        actions = self._extract_actions(text)
        constraints = self._extract_constraints(text)
        obligations = self._extract_obligations(text)
        permissions = self._extract_permissions(text)
        prohibitions = self._extract_prohibitions(text)
        jurisdiction = self._extract_jurisdiction(text)
        compliance_tags = self._extract_compliance_tags(text)
        privacy_rules = self._extract_privacy_rules(text)

        parsed = ParsedPolicy(
            policy_id=policy_id,
            original_text=text,
            entities=entities,
            actions=actions,
            constraints=constraints,
            obligations=obligations,
            permissions=permissions,
            prohibitions=prohibitions,
            jurisdiction=jurisdiction,
            compliance_tags=compliance_tags,
            privacy_rules=privacy_rules
        )
        self.parsed_policies.append(parsed)
        return parsed

    def parse_batch(self, policy_texts: List[tuple]) -> List[ParsedPolicy]:
        results = []
        for policy_id, text in policy_texts:
            results.append(self.parse(policy_id, text))
        return results

    def _extract_entities(self, text: str) -> List[ParsedEntity]:
        entities = []
        text_lower = text.lower()

        for entity_type, keywords in ENTITY_PATTERNS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    entities.append(ParsedEntity(
                        name=keyword,
                        type=entity_type,
                        roles=["subject" if "cannot" in text_lower or "must not" in text_lower else "object"]
                    ))

        return entities

    def _extract_actions(self, text: str) -> List[ParsedAction]:
        actions = []
        text_lower = text.lower()

        for action_type, verbs in ACTION_VERBS.items():
            for verb in verbs:
                if verb in text_lower:
                    actions.append(ParsedAction(
                        verb=verb,
                        target=self._extract_target(text, verb),
                        modality=self._determine_modality(text)
                    ))

        return actions

    def _extract_target(self, text: str, verb: str) -> Optional[str]:
        patterns = [
            rf"{verb}\s+([^\s]+(?:\s+[^\s]+)?)",
            rf"from\s+([^\s]+)",
            rf"to\s+([^\s]+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1)
        return None

    def _determine_modality(self, text: str) -> str:
        text_lower = text.lower()
        if "cannot" in text_lower or "must not" in text_lower or "may not" in text_lower:
            return "prohibition"
        elif "must" in text_lower or "require" in text_lower:
            return "obligation"
        elif "can" in text_lower or "may" in text_lower:
            return "permission"
        return "obligation"

    def _extract_constraints(self, text: str) -> List[ParsedConstraint]:
        constraints = []
        text_lower = text.lower()

        epsilon_match = re.search(r"epsilon\s*(?:must|should|remain|be)\s*(?:below|greater than|equal to)?\s*([\d.]+)", text_lower)
        if epsilon_match:
            constraints.append(ParsedConstraint(
                attribute="epsilon",
                operator="<",
                value=float(epsilon_match.group(1))
            ))

        budget_match = re.search(r"budget\s*(?:must|should|remain)\s*(?:below|under|above)\s*([\d.]+)", text_lower)
        if budget_match:
            constraints.append(ParsedConstraint(
                attribute="privacy_budget",
                operator="<",
                value=float(budget_match.group(1))
            ))

        region_match = re.search(r"(?:cannot|may not|must not)\s+(?:leave|transfer|move)\s+(?:outside\s+)?(?:the\s+)?(?:national\s+)?borders", text_lower)
        if region_match:
            constraints.append(ParsedConstraint(
                attribute="region",
                operator="not_in",
                value="national borders"
            ))
        else:
            region_match = re.search(r"(?:cannot|may not|must not)\s+(?:leave|transfer|move)\s+([^,\.]+)", text_lower)
            if region_match:
                constraints.append(ParsedConstraint(
                    attribute="region",
                    operator="not_in",
                    value=region_match.group(1).strip()
                ))

        localization_match = re.search(r"(?:must|should)\s+(?:remain|stay|be)\s+within\s+([^,\.]+)", text_lower)
        if localization_match:
            constraints.append(ParsedConstraint(
                attribute="localization",
                operator="in",
                value=localization_match.group(1).strip()
            ))

        return constraints

    def _extract_obligations(self, text: str) -> List[str]:
        obligations = []
        text_lower = text.lower()

        if "must" in text_lower or "require" in text_lower:
            if "cannot" not in text_lower and "may not" not in text_lower:
                obligations.append("mandatory_action")

        return obligations

    def _extract_permissions(self, text: str) -> List[str]:
        permissions = []
        text_lower = text.lower()

        if "can" in text_lower or "may" in text_lower:
            if "cannot" not in text_lower and "may not" not in text_lower:
                permissions.append("allowed_action")

        return permissions

    def _extract_prohibitions(self, text: str) -> List[str]:
        prohibitions = []
        text_lower = text.lower()

        if "cannot" in text_lower or "must not" in text_lower or "may not" in text_lower:
            prohibitions.append("forbidden_action")

        return prohibitions

    def _extract_jurisdiction(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        jurisdictions = ["EU", "US", "India", "UK", "Germany", "France", "California"]

        for jurisdiction in jurisdictions:
            if jurisdiction.lower() in text_lower:
                return jurisdiction

        if "national" in text_lower:
            return "national"

        return None

    def _extract_compliance_tags(self, text: str) -> List[str]:
        tags = []
        text_lower = text.lower()

        compliance_frameworks = ["HIPAA", "GDPR", "FSSAI", "PCI", "SOC2"]
        for framework in compliance_frameworks:
            if framework.lower() in text_lower:
                tags.append(framework)

        return tags

    def _extract_privacy_rules(self, text: str) -> List[str]:
        rules = []
        text_lower = text.lower()

        if "privacy" in text_lower or "differential" in text_lower or "epsilon" in text_lower:
            rules.append("privacy_requirement")

        if "consent" in text_lower:
            rules.append("consent_requirement")

        if "minimization" in text_lower:
            rules.append("data_minimization")

        if "localization" in text_lower or "cannot leave" in text_lower or "must remain" in text_lower:
            rules.append("data_localization")

        if "epsilon" in text_lower:
            value_match = re.search(r"below\s*([\d.]+)", text_lower)
            if value_match:
                rules.append(f"epsilon_threshold_{value_match.group(1)}")

        return rules
