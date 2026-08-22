"""Quickstart example for KAVP."""
import kavp

print(f"KAVP version: {kavp.__version__}")

ingestion = kavp.PolicyIngestion()
policies = ingestion.load_scenario("healthcare")

parser = kavp.PolicyParser()
parsed_policies = [parser.parse(p.source_id, p.text) for p in policies]

builder = kavp.GraphBuilder()
graph = builder.build_graph(parsed_policies, "quickstart")

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

orchestrator = kavp.FederatedOrchestrator(builder)
nodes = kavp.DemoNodeFactory.get_nodes("healthcare")
orchestrator.register_nodes(nodes)
results = engine.evaluate_all_nodes(nodes, parsed_policies)
task = orchestrator.create_task("Healthcare Task", results)

print(f"Selected: {task.selected_nodes}")
print(f"Blocked: {task.blocked_nodes}")
print(f"Rationale: {task.rationale}")
