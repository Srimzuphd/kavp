"""KAVP Visualization: policy graph visualization using PyVis."""
from __future__ import annotations
import os
import tempfile
from typing import List, Optional

from kavp.core.policy_ingestion import PolicyIngestion
from kavp.core.parser import PolicyParser
from kavp.core.graph_builder import GraphBuilder

try:
    from pyvis.network import Network
    _PYVIS_AVAILABLE = True
except ImportError:
    _PYVIS_AVAILABLE = False

try:
    import networkx as nx
    _NX_AVAILABLE = True
except ImportError:
    _NX_AVAILABLE = False

try:
    import plotly.express as px
    import plotly.graph_objects as go
    _PLOTLY_AVAILABLE = True
except ImportError:
    _PLOTLY_AVAILABLE = False


NODE_COLORS = {
    "policy": "#3B82F6",
    "entity": "#10B981",
    "constraint": "#EF4444",
    "action": "#F59E0B",
    "jurisdiction": "#8B5CF6",
    "compliance": "#6366F1",
    "prohibition": "#DC2626",
    "unknown": "#9CA3AF",
}


def visualize_policy_graph(
    builder: GraphBuilder,
    output_path: Optional[str] = None,
    height: str = "500px",
    width: str = "100%",
) -> str:
    if not _PYVIS_AVAILABLE:
        raise RuntimeError("PyVis is required for visualization. Install with: pip install 'kavp[viz]'")
    if not _NX_AVAILABLE:
        raise RuntimeError("NetworkX is required for visualization. Install with: pip install 'kavp[viz]'")

    G = builder.get_graph()
    net = Network(height=height, width=width, directed=True, bgcolor="#0e1117", font_color="white")
    net.barnes_hut()

    node_sizes = {}
    for node_id, attrs in G.nodes(data=True):
        node_type = attrs.get("node_type", "unknown")
        color = NODE_COLORS.get(node_type, NODE_COLORS["unknown"])
        size = 30 if node_type == "policy" else 20
        net.add_node(
            node_id,
            label=attrs.get("label", node_id),
            color=color,
            size=size,
            title=f"{node_type}: {attrs.get('label', node_id)}",
        )
        node_sizes[node_id] = size

    for u, v, data in G.edges(data=True):
        net.add_edge(u, v, title=data.get("label", "related"), color="#4b5563", arrows="to")

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".html")
        os.close(fd)

    net.save_graph(output_path)
    return output_path


def visualize_constraint_results(
    results: dict,
    output_path: Optional[str] = None,
) -> str:
    if not _PLOTLY_AVAILABLE:
        raise RuntimeError("Plotly is required for visualization. Install with: pip install 'kavp[viz]'")

    node_ids = list(results.keys())
    scores = [results[nid].compliance_score for nid in node_ids]
    eligible = [results[nid].eligible for nid in node_ids]

    colors = ["#10B981" if e else "#EF4444" for e in eligible]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=node_ids,
        y=scores,
        marker_color=colors,
        text=[f"{s:.1f}%" for s in scores],
        textposition="auto",
    ))
    fig.update_layout(
        title="Node Compliance Scores",
        xaxis_title="Node ID",
        yaxis_title="Compliance Score (%)",
        yaxis=dict(range=[0, 105]),
        template="plotly_dark",
    )
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".html")
        os.close(fd)
    fig.write_html(output_path)
    return output_path


def demo_visualization():
    ingestion = PolicyIngestion()
    policies = ingestion.load_scenario("healthcare")
    parser = PolicyParser()
    parsed = [parser.parse(p.source_id, p.text) for p in policies]
    builder = GraphBuilder()
    builder.build_graph(parsed, "viz_demo")

    html_path = visualize_policy_graph(builder)
    print(f"Policy graph visualization saved to: {html_path}")

    from kavp.core.constraint_engine import ConstraintPropagation, NodeProfile
    from kavp.core.orchestrator import DemoNodeFactory
    engine = ConstraintPropagation(builder)
    nodes = DemoNodeFactory.get_nodes("healthcare")
    results = engine.evaluate_all_nodes(nodes, parsed)
    scores_path = visualize_constraint_results(results)
    print(f"Constraint results visualization saved to: {scores_path}")


if __name__ == "__main__":
    demo_visualization()
