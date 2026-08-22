"""Packaging tests for KAVP."""
import kavp


def test_import_kavp():
    assert kavp is not None


def test_version_available():
    assert hasattr(kavp, "__version__")
    assert isinstance(kavp.__version__, str)
    assert len(kavp.__version__) > 0


def test_public_api_imports():
    assert hasattr(kavp, "PolicyIngestion")
    assert hasattr(kavp, "PolicyParser")
    assert hasattr(kavp, "GraphBuilder")
    assert hasattr(kavp, "ConstraintPropagation")
    assert hasattr(kavp, "NodeProfile")
    assert hasattr(kavp, "FederatedOrchestrator")
    assert hasattr(kavp, "DemoNodeFactory")
    assert hasattr(kavp, "AuditLogger")


def test_no_import_side_effects():
    import importlib
    import sys
    mods_before = set(sys.modules.keys())
    importlib.reload(kavp)
    mods_after = set(sys.modules.keys())
    new_mods = mods_after - mods_before
    # Only kavp and its core/gdpr submodules should be loaded
    unexpected = [m for m in new_mods if "torch" in m or "flwr" in m or "sklearn" in m]
    assert not unexpected, f"Unexpected heavy imports: {unexpected}"


def test_package_resources():
    import importlib.resources as resources
    assert resources.files("kavp").is_dir()


def test_quickstart():
    ingestion = kavp.PolicyIngestion()
    policies = ingestion.load_scenario("healthcare")
    assert len(policies) > 0

    parser = kavp.PolicyParser()
    parsed = [parser.parse(p.source_id, p.text) for p in policies]
    assert len(parsed) > 0

    builder = kavp.GraphBuilder()
    graph = builder.build_graph(parsed, "test")
    assert len(graph.nodes) > 0

    profile = kavp.NodeProfile(
        node_id="TEST", name="Test", region="EU", domain="healthcare",
        compliance_tags=["GDPR"]
    )
    engine = kavp.ConstraintPropagation(builder)
    result = engine.evaluate_node(profile, parsed)
    assert hasattr(result, "eligible")
    assert hasattr(result, "compliance_score")
