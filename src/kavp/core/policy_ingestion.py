from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class PolicySource(BaseModel):
    source_id: str
    category: str
    text: str
    loaded_at: datetime = Field(default_factory=datetime.now)


class SamplePolicies:
    HEALTHCARE = [
        "EU patient data cannot leave EU region",
        "Differential privacy epsilon must remain below 2.0",
        "Only HIPAA-compliant hospital nodes may participate",
        "Medical data transfers require explicit patient consent",
        "GDPR compliance required for all EU patient data processing"
    ]

    FOOD_TECH = [
        "Food safety data must not be transferred outside approved facilities",
        "FSSAI compliance required for all food testing nodes",
        "Temperature-sensitive food data must remain within cold chain facilities",
        "Food inspection results cannot leave national borders without approval",
        "HACCP compliance required for food safety processing"
    ]

    FINANCE = [
        "Bank account data must remain within EU for GDPR compliance",
        "Financial transactions require consent from all parties",
        "Credit scores cannot be shared with unauthorized third parties",
        "Transaction data must not leave licensed financial institutions",
        "PCI-DSS compliance required for all payment processing"
    ]

    GENERAL = [
        "Data localization requirements apply to sensitive personal information",
        "Cross-border data transfers require adequacy decisions",
        "Privacy by design must be implemented in all systems",
        "Data minimization principles apply to all collected information"
    ]


class PolicyIngestion:
    def __init__(self):
        self.loaded_policies: List[PolicySource] = []
        self.scenarios = {
            "healthcare": SamplePolicies.HEALTHCARE,
            "food_tech": SamplePolicies.FOOD_TECH,
            "finance": SamplePolicies.FINANCE,
            "general": SamplePolicies.GENERAL
        }

    def load_scenario(self, scenario: str) -> List[PolicySource]:
        policy_texts = self.scenarios.get(scenario.lower(), SamplePolicies.GENERAL)
        self.loaded_policies = []
        for i, text in enumerate(policy_texts):
            self.loaded_policies.append(PolicySource(
                source_id=f"POL-{scenario.upper()[:3]}-{i+1:03d}",
                category=scenario,
                text=text
            ))
        return self.loaded_policies

    def add_custom_policy(self, text: str, category: str = "custom") -> PolicySource:
        policy = PolicySource(
            source_id=f"POL-CUS-{len(self.loaded_policies)+1:03d}",
            category=category,
            text=text
        )
        self.loaded_policies.append(policy)
        return policy

    def get_all_texts(self) -> List[str]:
        return [p.text for p in self.loaded_policies]

    def clear(self):
        self.loaded_policies = []
