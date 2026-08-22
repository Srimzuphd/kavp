"""
KAVP Policy Graph Generation — End-to-End Walkthrough
======================================================

This script is designed for junior engineers. It walks through every step
of turning raw policy text into a typed, attributed, directed graph that
can be used for federated-node compliance evaluation.

Run:
    python /home/dell/kavp/pipp/examples/quickstart/policy_graph_walkthrough.py
"""
from __future__ import annotations
import textwrap
from typing import List

from kavp.core.policy_ingestion import PolicyIngestion, SamplePolicies
from kavp.core.parser import PolicyParser, ParsedPolicy
from kavp.core.graph_builder import GraphBuilder
from kavp.core.constraint_engine import ConstraintPropagation, NodeProfile
from kavp.core.orchestrator import DemoNodeFactory


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def section(title: str):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def subsection(title: str):
    print()
    print("-" * 70)
    print(f"  {title}")
    print("-" * 70)


def explain(msg: str):
    print(f"\n>> {msg}")


def show_dict(d: dict, indent: int = 2):
    import json
    print(json.dumps(d, indent=indent, default=str))


# ----------------------------------------------------------------------
# Step 1: Load raw policy text
# ----------------------------------------------------------------------
def step1_load_policies():
    section("STEP 1 — Load Raw Policy Text")

    explain("Policies are just strings of natural-language rules. "
            "KAVP ships with sample scenarios (healthcare, food, finance).")

    ingestion = PolicyIngestion()
    policies = ingestion.load_scenario("healthcare")

    print(f"\nLoaded {len(policies)} healthcare policies:\n")
    for i, p in enumerate(policies, 1):
        print(f"  [{i}] {p.source_id}")
        print(f"      \"{p.text}\"")
        print()

    return policies


# ----------------------------------------------------------------------
# Step 2: Parse policies into structured objects
# ----------------------------------------------------------------------
def step2_parse_policies(policies):
    section("STEP 2 — Parse Policies Into Structured Objects")

    explain("The parser reads each sentence and extracts:")
    explain("  - entities (data, region, organization, person, system)")
    explain("  - actions (transfer, access, process, store)")
    explain("  - constraints (epsilon < 2.0, region restrictions, etc.)")
    explain("  - obligations, permissions, prohibitions")
    explain("  - jurisdiction tags (EU, US, India, UK)")
    explain("  - compliance tags (HIPAA, GDPR, PCI, FSSAI)")

    parser = PolicyParser()
    parsed: List[ParsedPolicy] = []

    for p in policies:
        parsed_policy = parser.parse(p.source_id, p.text)
        parsed.append(parsed_policy)

        print(f"\n--- {parsed_policy.policy_id} ---")
        print(f"Original text: \"{parsed_policy.original_text}\"")
        print(f"Jurisdiction : {parsed_policy.jurisdiction}")

        if parsed_policy.entities:
            print(f"Entities     : {[e.name + ' (' + e.type + ')' for e in parsed_policy.entities]}")
        if parsed_policy.actions:
            print(f"Actions      : {[a.verb + ' -> ' + str(a.target) for a in parsed_policy.actions]}")
        if parsed_policy.constraints:
            for c in parsed_policy.constraints:
                print(f"Constraint   : {c.attribute} {c.operator} {c.value}")
        if parsed_policy.obligations:
            print(f"Obligations  : {parsed_policy.obligations}")
        if parsed_policy.permissions:
            print(f"Permissions  : {parsed_policy.permissions}")
        if parsed_policy.prohibitions:
            print(f"Prohibitions : {parsed_policy.prohibitions}")
        if parsed_policy.compliance_tags:
            print(f"Compliance   : {parsed_policy.compliance_tags}")

    return parsed


# ----------------------------------------------------------------------
# Step 3: Build the policy graph
# ----------------------------------------------------------------------
def step3_build_graph(parsed):
    section("STEP 3 — Build the Policy Graph")

    explain("The GraphBuilder turns ParsedPolicy objects into a directed graph.")
    explain("Each item becomes a NODE. Relationships become EDGES.")
    explain("Node types are colored/typed so later we can traverse them.")

    builder = GraphBuilder()
    policy_graph = builder.build_graph(parsed, graph_id="walkthrough")

    G = builder.get_graph()
    print(f"\nGraph ID      : {policy_graph.graph_id}")
    print(f"Total nodes   : {len(G.nodes)}")
    print(f"Total edges   : {len(G.edges)}")

    print("\n--- Nodes ---")
    for node_id, attrs in G.nodes(data=True):
        nt = attrs.get("node_type", "unknown")
        label = attrs.get("label", node_id)
        print(f"  [{node_id}] type={nt}, label={label}")

    print("\n--- Edges ---")
    for u, v, data in G.edges(data=True):
        et = data.get("edge_type", "related")
        label = data.get("label", et)
        print(f"  {u} --[{et}]--> {v}  (label={label})")

    explain("Notice how policies connect to entities, constraints, actions, "
            "and compliance tags. This is the KAVP-PGC substrate.")

    return builder


# ----------------------------------------------------------------------
# Step 4: Understand the graph topology
# ----------------------------------------------------------------------
def step4_graph_topology(builder):
    section("STEP 4 — Graph Topology / Metadata")

    explain("GraphBuilder also stores metadata so we can inspect richer "
            "details about each node later.")

    G = builder.get_graph()
    print("\nNode metadata examples:\n")

    for node_id in list(G.nodes)[:6]:
        meta = builder.node_metadata.get(node_id, {})
        print(f"  {node_id}:")
        for k, v in meta.items():
            if isinstance(v, str) and len(v) > 80:
                v = v[:80] + "..."
            print(f"    {k}: {v}")
        print()


# ----------------------------------------------------------------------
# Step 5: Create a federated node profile
# ----------------------------------------------------------------------
def step5_node_profile():
    section("STEP 5 — Create a Federated Node Profile")

    explain("A federated participant (hospital, bank, lab) is represented "
            "as a NodeProfile. This is the 'A(n_i)' attribute vector from "
            "the KAVP equations.")

    profile = NodeProfile(
        node_id="HOSP_A",
        name="Hospital A (Berlin)",
        region="EU",
        domain="healthcare",
        compliance_tags=["HIPAA", "GDPR"],
        privacy_budget=1.5,
        epsilon=1.8,
    )

    print("\nNodeProfile attributes:")
    print(f"  node_id        : {profile.node_id}")
    print(f"  name           : {profile.name}")
    print(f"  region         : {profile.region}")
    print(f"  domain         : {profile.domain}")
    print(f"  compliance_tags: {profile.compliance_tags}")
    print(f"  privacy_budget : {profile.privacy_budget}")
    print(f"  epsilon        : {profile.epsilon}")

    explain("This profile will be tested against every constraint in the graph.")

    return profile


# ----------------------------------------------------------------------
# Step 6: Evaluate the node against the graph
# ----------------------------------------------------------------------
def step6_evaluate(builder, profile):
    section("STEP 6 — Evaluate Node Against Policy Graph")

    explain("ConstraintPropagation walks the graph, finds constraints that "
            "apply to this node's region/domain, and runs the predicates.")

    engine = ConstraintPropagation(builder)
    result = engine.evaluate_node(profile, [])

    print(f"\nNode ID      : {result.node_id}")
    print(f"Node Name    : {result.node_name}")
    print(f"Eligible     : {result.eligible}")
    print(f"Score        : {result.compliance_score:.1f}%")
    print(f"Violations   : {result.violations}")
    print(f"Warnings     : {result.warnings}")
    print(f"Decision     : {result.decision_reason}")

    explain("Score = 100% means no violations. "
            "Each violation drops the score by penalty %.")

    return result


# ----------------------------------------------------------------------
# Step 7: Evaluate multiple nodes (orchestration demo)
# ----------------------------------------------------------------------
def step7_orchestration(builder):
    section("STEP 7 — Federated Orchestration (Multiple Nodes)")

    explain("In a real FL round, we evaluate ALL candidate nodes, then "
            "select only the eligible ones. This is orchestration.")

    parser = PolicyParser()
    ingestion = PolicyIngestion()
    policies = ingestion.load_scenario("healthcare")
    parsed = [parser.parse(p.source_id, p.text) for p in policies]

    engine = ConstraintPropagation(builder)
    nodes = DemoNodeFactory.get_nodes("healthcare")

    explain(f"Loaded {len(nodes)} demo hospital nodes.")
    explain("Evaluating each node against the healthcare policy graph...\n")

    results = engine.evaluate_all_nodes(nodes, parsed)

    eligible = []
    blocked = []

    for nid, r in results.items():
        status = "ELIGIBLE" if r.eligible else "BLOCKED"
        print(f"  {r.node_name:35s} | {status:10s} | Score: {r.compliance_score:6.1f}%")
        if r.eligible:
            eligible.append(r)
        else:
            blocked.append(r)

    print(f"\nEligible: {len(eligible)} | Blocked: {len(blocked)}")

    explain("Eligible nodes can participate in the federated training round. "
            "Blocked nodes are excluded until they fix their compliance gaps.")

    return results


# ----------------------------------------------------------------------
# Step 8: Full pipeline recap
# ----------------------------------------------------------------------
def step8_recap():
    section("STEP 8 — End-to-End Recap")

    recap = """
The full KAVP policy graph pipeline:

  1. Policy Ingestion   : Load raw text policies
                          ↓
  2. Semantic Parsing   : Extract entities, actions, constraints,
                          obligations, permissions, prohibitions
                          ↓
  3. Graph Construction : Build typed directed graph (nodes + edges)
                          - policies connect to entities/constraints/actions
                          - edges encode appliesTo, governs, requires, prohibits
                          ↓
  4. Graph Metadata     : Store rich metadata for visualization and audit
                          ↓
  5. Node Profiles      : Each FL participant has attributes A(n_i)
                          - region, domain, tags, epsilon, etc.
                          ↓
  6. Constraint Eval    : For each node, collect applicable constraints
                          and evaluate predicates:
                            Satisfies(n_i, c) in {0,1}
                            Compliance(n_i, C) = prod_c Satisfies(n_i, c)
                            Cost(n_i) = sum_c w_c (1 - Satisfies)
                            Feasibility(n_i) = 1 iff Compliance>=tau AND Cost<=kappa
                          ↓
  7. Orchestration      : Select eligible nodes, block violations,
                          generate audit evidence, run FL round

Key concepts:
  - Graph is POLICY-CENTRIC. Nodes are policies/constraints, not participants.
  - Node profiles are evaluated DYNAMICALLY against the graph each round.
  - The same graph can evaluate many different participants.
  - Policy updates (new version) create a new graph; VersionHandler tracks migration.
    """
    print(recap)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    print("""
    __  __           _        __   __
   |  \\/  | ___  ___| |_ ___  \\ \\ / / _ __ ___
   | |\\/| |/ _ \\/ __| __/ _ \\  \\ V /| '__/ _ \\
   | |  | |  __/\\__ \\ ||  __/   | | | | | (_) |
   |_|  |_|\\___||___/\\__\\___|   |_| |_|_|\\___/

   Policy Graph Generation — End-to-End Walkthrough
   """)

    policies = step1_load_policies()
    parsed = step2_parse_policies(policies)
    builder = step3_build_graph(parsed)
    step4_graph_topology(builder)
    profile = step5_node_profile()
    step6_evaluate(builder, profile)
    step7_orchestration(builder)
    step8_recap()

    print("\n" + "=" * 70)
    print("  Walkthrough complete.")
    print("  Next: explore /home/dell/kavp/pipp/examples/quickstart/")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
