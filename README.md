# KAVP

**K**nowledge-based **A**ware **V**erifiable **P**olicy framework for federated AI research and orchestration.

KAVP is an open-source framework for policy-aware, governance-aware, and context-aware federated AI research and orchestration. It provides typed policy graphs, constraint propagation, defeasible conflict resolution, and audit-ready evidence logging.

> **Status:** Research framework (v0.1.1). APIs may change before 1.0.

## What is KAVP?

KAVP enables researchers and developers to:

- Represent policies as typed, attributed, directed graphs
- Propagate constraints across federated node profiles
- Resolve conflicts between regulatory and organizational policies
- Generate auditable evidence with chained-hash integrity
- Orchestrate federated tasks while maintaining compliance

KAVP research spans policy-aware and governance-aware federated AI across multiple domains (healthcare, food safety, finance, etc.) without coupling the core to any single application.

## Core Capabilities

- **Policy Ingestion & Parsing** — Load and semantically parse natural-language policies into structured representations
- **Graph Construction** — Build typed policy graphs with entities, constraints, actions, and jurisdictions
- **Constraint Propagation** — Evaluate federated node profiles against active policies with compliance scoring
- **Defeasible Reasoning** — Resolve conflicts between competing rules using explicit superiority and precedence
- **Audit Logging** — Track all decisions with timestamps, severity levels, and exportable logs
- **GDPR Extension** — Ready-to-use GDPR Art.5–49 typed policy graph with transfer admissibility and evidence integrity

## Installation

```bash
pip install kavp
```

### Optional Dependencies

```bash
pip install "kavp[ml]"      # ML metrics, inference, unlearning
pip install "kavp[viz]"     # Dashboard and graph visualization
pip install "kavp[dev]"     # Build, test, and publish tools
pip install "kavp[all]"     # All optional dependencies
```

## Quick Start

```python
import kavp

print(kavp.__version__)

# Load a sample policy scenario
ingestion = kavp.PolicyIngestion()
policies = ingestion.load_scenario("healthcare")

# Parse policies
parser = kavp.PolicyParser()
parsed_policies = [parser.parse(p.source_id, p.text) for p in policies]

# Build policy graph
builder = kavp.GraphBuilder()
graph = builder.build_graph(parsed_policies, graph_id="demo")

# Evaluate a node
profile = kavp.NodeProfile(
    node_id="HOSP_A",
    name="Hospital A (Berlin)",
    region="EU",
    domain="healthcare",
    compliance_tags=["HIPAA", "GDPR"],
    epsilon=1.8
)
engine = kavp.ConstraintPropagation(builder)
result = engine.evaluate_node(profile, parsed_policies)
print(f"Eligible: {result.eligible}, Score: {result.compliance_score}")
```

## Architecture

```
kavp/
├── core/            # Policy ingestion, parsing, graph, constraints, orchestration
├── gdpr/            # GDPR typed policy graph and defeasible resolution
├── metrics/         # Classification, inference, MIA, and unlearning metrics [ml]
├── utils/           # Shared utilities
└── cli/             # Command-line interface
```

## Federated AI Integration

KAVP is designed to complement existing FL runtimes (Flower, FATE, PySyft, etc.) through adapters. The core package remains domain-neutral and dependency-light. Optional adapters can be installed separately.

## Policy and Governance

KAVP enforces:

- Data localization and cross-border transfer rules
- Differential privacy budget constraints
- Consent and lawful-basis validation
- Compliance framework requirements (HIPAA, GDPR, PCI-DSS, FSSAI)
- Human-review escalation for conditional or exception cases

## Examples

See the `examples/` directory for runnable notebooks and scripts.

## Research Background

KAVP builds on peer-reviewed research in policy-aware federated learning, including:

- KAVP-PGC: Knowledge-Based Policy Graph Construction
- KAVP-GDPR: GDPR-aware federated orchestration with typed policy graphs and chained-hash evidence

## Citation

If you use KAVP in academic work, please cite the associated papers. See `CITATION.cff` for metadata.

## Documentation

Full documentation is available at [https://kavp.github.io](https://kavp.github.io).

## Contributing

See `CONTRIBUTING.md` for development setup and guidelines.

## License

MIT License. See `LICENSE` for details.

## Disclaimer

KAVP is a research framework. It does not provide legal advice or compliance certification.
