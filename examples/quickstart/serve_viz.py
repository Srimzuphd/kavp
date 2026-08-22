"""Serve KAVP visualizations on port 8045."""
from __future__ import annotations
import os
import sys
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler

from kavp.core.policy_ingestion import PolicyIngestion
from kavp.core.parser import PolicyParser
from kavp.core.graph_builder import GraphBuilder
from kavp.core.constraint_engine import ConstraintPropagation
from kavp.core.orchestrator import DemoNodeFactory

try:
    from pyvis.network import Network
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyvis", "plotly", "-q"])
    from pyvis.network import Network

import plotly.graph_objects as go
from plotly.subplots import make_subplots


PORT = 8045
OUTPUT_DIR = "/home/dell/kavp/pipp/examples/quickstart/viz_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


NODE_COLORS = {
    "policy":     "#3B82F6",
    "entity":     "#10B981",
    "constraint": "#EF4444",
    "action":     "#F59E0B",
    "jurisdiction": "#8B5CF6",
    "compliance": "#6366F1",
    "prohibition": "#DC2626",
    "unknown":    "#9CA3AF",
}

EDGE_COLORS = {
    "appliesTo":           "#3B82F6",
    "governs":             "#F59E0B",
    "requires":            "#EF4444",
    "prohibits":           "#DC2626",
    "targets":             "#F59E0B",
    "excepts":             "#10B981",
    "jurisdiction":        "#8B5CF6",
    "appliesIn":           "#8B5CF6",
    "requiresCompliance": "#6366F1",
    "related":             "#4b5563",
}

EDGE_DASH = {
    "prohibits": True,
    "excepts":   True,
}


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def build_policy_html(ingestion, parser, builder):
    G = builder.get_graph()
    net = Network(height="600px", width="100%", directed=True, bgcolor="#0d1117", font_color="#c9d1d9")
    net.barnes_hut()
    net.toggle_physics(False)
    net.set_options("""
    {
      "nodes": {
        "borderWidth": 2,
        "borderColor": "rgba(255,255,255,0.2)",
        "shadow": {"enabled": true, "size": 5}
      },
      "edges": {
        "color": {"opacity": 0.6},
        "smooth": {"type": "continuous"}
      },
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -3000,
          "centralGravity": 0.3,
          "springLength": 200,
          "springConstant": 0.04
        }
      }
    }
    """)

    node_data = {}
    for node_id, attrs in G.nodes(data=True):
        nt = attrs.get("node_type", "unknown")
        color = NODE_COLORS.get(nt, NODE_COLORS["unknown"])
        size = 35 if nt == "policy" else 22

        meta = builder.node_metadata.get(node_id, {})
        label = attrs.get("label", node_id)

        title_parts = [f"<b>{nt.upper()}</b>"]
        if meta.get("original_text"):
            text = meta["original_text"]
            if len(text) > 120:
                text = text[:120] + "..."
            title_parts.append(f"<i>Policy:</i> {text}")
        if meta.get("compliance_tags"):
            title_parts.append(f"<i>Tags:</i> {', '.join(meta['compliance_tags'])}")
        if meta.get("privacy_rules"):
            title_parts.append(f"<i>Rules:</i> {', '.join(meta['privacy_rules'])}")
        title = "<br>".join(title_parts)

        net.add_node(node_id, label=label, color=color, size=size, title=title,
                     shape="dot" if nt == "constraint" else "diamond" if nt in ("obligation", "prohibition", "exception") else "dot")
        node_data[node_id] = {"type": nt, "color": color}

    for u, v, data in G.edges(data=True):
        et = data.get("edge_type", "related")
        color = EDGE_COLORS.get(et, EDGE_COLORS["related"])
        dash = EDGE_DASH.get(et, False)
        label = data.get("label", et)
        width = 2.0 if et in ("prohibits", "requires", "superior") else 1.0

        edge_title = f"<b>{et}</b>"
        meta_u = builder.node_metadata.get(u, {})
        meta_v = builder.node_metadata.get(v, {})
        u_label = meta_u.get("original_text", "")[:80]
        v_label = meta_v.get("label", v)[:80]
        if u_label:
            edge_title += f"<br><i>From:</i> {u_label}"
        if v_label:
            edge_title += f"<br><i>To:</i> {v_label}"

        kwargs = {"width": width}
        if dash:
            kwargs["dash"] = True
        net.add_edge(u, v, color=color, title=edge_title, label=label, **kwargs)

    path = os.path.join(OUTPUT_DIR, "policy_graph.html")
    net.save_graph(path)
    return path


def build_policy_list_html(parsed_policies):
    rows = ""
    for p in parsed_policies:
        obligations = ", ".join(f"<span class='tag ob'>{o}</span>" for o in p.obligations) if p.obligations else "—"
        permissions = ", ".join(f"<span class='tag perm'>{pm}</span>" for pm in p.permissions) if p.permissions else "—"
        prohibitions = ", ".join(f"<span class='tag prohib'>{pr}</span>" for pr in p.prohibitions) if p.prohibitions else "—"
        constraints = "<br>".join(f"{c.attribute} {c.operator} {c.value}" for c in p.constraints) if p.constraints else "—"
        entities = ", ".join(f"{e.name} ({e.type})" for e in p.entities) if p.entities else "—"
        tags = ", ".join(f"<span class='tag comp'>{t}</span>" for t in p.compliance_tags) if p.compliance_tags else "—"

        rows += f"""
        <div class="policy-card">
          <div class="policy-header">
            <span class="policy-id">{p.policy_id}</span>
            <span class="jurisdiction">{p.jurisdiction or '—'}</span>
          </div>
          <div class="policy-text">"{p.original_text}"</div>
          <div class="policy-meta">
            <div class="meta-row"><span class="meta-label">Entities</span><span class="meta-value">{entities}</span></div>
            <div class="meta-row"><span class="meta-label">Obligations</span><span class="meta-value">{obligations}</span></div>
            <div class="meta-row"><span class="meta-label">Permissions</span><span class="meta-value">{permissions}</span></div>
            <div class="meta-row"><span class="meta-label">Prohibitions</span><span class="meta-value">{prohibitions}</span></div>
            <div class="meta-row"><span class="meta-label">Constraints</span><span class="meta-value">{constraints}</span></div>
            <div class="meta-row"><span class="meta-label">Compliance</span><span class="meta-value">{tags}</span></div>
          </div>
        </div>"""

    return rows


def build_compliance_html(results, engine):
    nodes_by_status = {"eligible": [], "blocked": []}
    for nid, r in results.items():
        key = "eligible" if r.eligible else "blocked"
        nodes_by_status[key].append(r)

    node_cards = ""
    for category, nodes in nodes_by_status.items():
        for r in nodes:
            status_class = "eligible" if category == "eligible" else "blocked"
            node_cards += f"""
            <div class="node-card {status_class}">
              <div class="node-header">
                <span class="node-id">{r.node_id}</span>
                <span class="node-status">{category.upper()}</span>
                <span class="node-score">{r.compliance_score:.1f}%</span>
              </div>
              <div class="node-meta">
                <div class="meta-row"><span class="meta-label">Name</span><span class="meta-value">{r.node_name}</span></div>
                <div class="meta-row"><span class="meta-label">Violations</span><span class="meta-value">{'; '.join(r.violations) if r.violations else 'None'}</span></div>
                <div class="meta-row"><span class="meta-label">Warnings</span><span class="meta-value">{'; '.join(r.warnings) if r.warnings else 'None'}</span></div>
                <div class="meta-row"><span class="meta-label">Decision</span><span class="meta-value">{r.decision_reason}</span></div>
              </div>
            </div>"""

    legend = """
    <div class="graph-legend">
      <h3>Graph Legend</h3>
      <div class="legend-items">
        <div class="legend-item"><span class="legend-dot" style="background:#3B82F6"></span> Policy</div>
        <div class="legend-item"><span class="legend-dot" style="background:#10B981"></span> Entity</div>
        <div class="legend-item"><span class="legend-dot" style="background:#EF4444"></span> Constraint</div>
        <div class="legend-item"><span class="legend-dot" style="background:#F59E0B"></span> Action</div>
        <div class="legend-item"><span class="legend-dot" style="background:#8B5CF6"></span> Jurisdiction</div>
        <div class="legend-item"><span class="legend-dot" style="background:#6366F1"></span> Compliance</div>
        <div class="legend-item"><span class="legend-dot" style="background:#DC2626"></span> Prohibition</div>
        <div class="legend-item"><span class="legend-dot" style="background:#9CA3AF"></span> Unknown</div>
        <div class="legend-item"><span class="legend-dot" style="background:#4b5563"></span> Link</div>
        <div class="legend-item" style="margin-left:14px"><span style="border-bottom:2px dashed #DC2626;display:inline-block;width:20px"></span> Prohibition edge</div>
      </div>
      <h3>Edge Types</h3>
      <div class="legend-items">
        <div class="legend-item"><span class="legend-line" style="background:#3B82F6"></span> appliesTo</div>
        <div class="legend-item"><span class="legend-line" style="background:#F59E0B"></span> governs</div>
        <div class="legend-item"><span class="legend-line" style="background:#EF4444"></span> requires</div>
        <div class="legend-item"><span class="legend-line" style="background:#DC2626"></span> prohibits</div>
        <div class="legend-item"><span class="legend-line" style="background:#10B981"></span> excepts</div>
        <div class="legend-item"><span class="legend-line" style="background:#8B5CF6"></span> jurisdiction</div>
        <div class="legend-item"><span class="legend-line" style="background:#6366F1"></span> requiresCompliance</div>
      </div>
    </div>"""

    return node_cards, legend


def build_compliance_chart_html(results):
    node_ids = list(results.keys())
    scores = [results[nid].compliance_score for nid in node_ids]
    colors = ["#10B981" if results[nid].eligible else "#EF4444" for nid in node_ids]
    names = [results[nid].node_name for nid in node_ids]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=node_ids, y=scores, marker_color=colors,
                         text=[f"{s:.1f}%" for s in scores], textposition="outside",
                         hovertext=[f"{names[i]}: {scores[i]:.1f}%" for i in range(len(node_ids))]))
    fig.update_layout(title="Node Compliance Scores", xaxis_title="Node", yaxis_title="Score (%)",
                      yaxis=dict(range=[0, 110]), template="plotly_dark", margin_t=60)
    path = os.path.join(OUTPUT_DIR, "compliance_scores.html")
    fig.write_html(path)
    return path


def generate_all():
    print("[1/5] Loading healthcare policies...")
    ingestion = PolicyIngestion()
    policies = ingestion.load_scenario("healthcare")

    print("[2/5] Parsing policies...")
    parser = PolicyParser()
    parsed = [parser.parse(p.source_id, p.text) for p in policies]

    print("[3/5] Building policy graph + generating network visualization...")
    builder = GraphBuilder()
    builder.build_graph(parsed, "live_demo")
    graph_path = build_policy_html(ingestion, parser, builder)
    print(f"      -> {graph_path}")

    print("[4/5] Evaluating nodes + generating compliance views...")
    engine = ConstraintPropagation(builder)
    nodes = DemoNodeFactory.get_nodes("healthcare")
    results = engine.evaluate_all_nodes(nodes, parsed)

    policy_list_html = build_policy_list_html(parsed)
    node_cards_html, legend_html = build_compliance_html(results, engine)
    chart_path = build_compliance_chart_html(results)
    print(f"      -> {chart_path}")

    print("[5/5] Generating dashboard...")
    eligible_count = sum(1 for r in results.values() if r.eligible)
    blocked_count = sum(1 for r in results.values() if not r.eligible)
    total_constraints = sum(len(p.constraints) for p in parsed)

    index_html = f"""<!DOCTYPE html>
<html><head><title>KAVP Visualization Dashboard</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px 30px; line-height: 1.5; }}
h1 {{ color: #58a6ff; font-size: 28px; margin-bottom: 5px; }}
h2 {{ color: #8b949e; font-size: 18px; margin-top: 30px; margin-bottom: 10px; border-bottom: 1px solid #21262d; padding-bottom: 10px; }}
.subtitle {{ color: #8b949e; font-size: 14px; margin-bottom: 30px; }}
.stats {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
.stat-box {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px 20px; min-width: 120px; text-align: center; }}
.stat-box .stat-number {{ font-size: 28px; font-weight: bold; }}
.stat-box .stat-label {{ font-size: 12px; color: #8b949e; }}
.stat-box.eligible {{ border-color: #10B981; }} .stat-box.eligible .stat-number {{ color: #10B981; }}
.stat-box.blocked {{ border-color: #EF4444; }} .stat-box.blocked .stat-number {{ color: #EF4444; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; margin-bottom: 20px; }}
.card h2 {{ margin-top: 0; }}
.graph-container {{ display: flex; gap: 20px; }}
.graph-main {{ flex: 1; min-width: 0; }}
.graph-info {{ width: 320px; flex-shrink: 0; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 15px; max-height: 620px; overflow-y: auto; }}
.graph-info h3 {{ color: #58a6ff; font-size: 14px; margin-top: 12px; margin-bottom: 6px; }}
.graph-info p {{ font-size: 12px; color: #8b949e; margin-bottom: 8px; }}
.graph-info ul {{ font-size: 12px; color: #c9d1d9; padding-left: 16px; margin-bottom: 8px; }}
.graph-info li {{ margin-bottom: 4px; }}
.graph-info .tag {{ display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; margin-right: 3px; }}
.graph-info .tag.ob {{ background: #1f6feb33; color: #ffffff; }}
.graph-info .tag.perm {{ background: #238636; color: #ffffff; }}
.graph-info .tag.prohib {{ background: #da3633; color: #ffffff; }}
.graph-info .tag.comp {{ background: #1f6feb33; color: #ffffff; }}
.graph-info code {{ background: #161b22; padding: 1px 6px; border-radius: 4px; font-size: 11px; color: #e6edf3; }}
iframe {{ border: 1px solid #30363d; border-radius: 8px; width: 100%; height: 600px; }}

.policy-card {{ background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin-bottom: 10px; }}
.policy-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
.policy-id {{ background: #3B82F6; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
.jurisdiction {{ background: #8B5CF6; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; }}
.policy-text {{ color: #e6edf3; font-style: italic; margin-bottom: 8px; border-left: 3px solid #30363d; padding-left: 10px; }}
.policy-meta {{ font-size: 13px; }}
.meta-row {{ display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid #21262d; }}
.meta-label {{ color: #8b949e; font-size: 12px; min-width: 90px; }}
.meta-value {{ color: #c9d1d9; text-align: right; flex: 1; font-size: 12px; padding-left: 10px; }}
.tag {{ display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; margin-right: 3px; }}
.tag.ob {{ background: #1f6feb33; color: #ffffff; }}
.tag.perm {{ background: #238636; color: #ffffff; }}
.tag.prohib {{ background: #da3633; color: #ffffff; }}
.tag.comp {{ background: #1f6feb33; color: #ffffff; }}

.node-card {{ background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin-bottom: 10px; }}
.node-card.eligible {{ border-left: 3px solid #10B981; }}
.node-card.blocked {{ border-left: 3px solid #EF4444; }}
.node-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
.node-id {{ font-weight: 600; color: #e6edf3; }}
.node-status {{ padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
.eligible .node-status {{ background: #238636; color: #ffffff; }}
.blocked .node-status {{ background: #da3633; color: #ffffff; }}
.node-score {{ color: #8b949e; font-size: 13px; }}
.node-meta {{ font-size: 13px; }}

.graph-legend {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px 20px; margin-bottom: 20px; }}
.graph-legend h3 {{ color: #c9d1d9; font-size: 14px; margin-bottom: 10px; }}
.legend-items {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px; }}
.legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 12px; color: #8b949e; }}
.legend-dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
.legend-line {{ width: 24px; height: 3px; border-radius: 2px; display: inline-block; }}
</style></head><body>
<h1>KAVP Visualization Dashboard</h1>
<p class="subtitle">Policy-aware and governance-aware federated AI research framework</p>

<div class="stats">
  <div class="stat-box"><div class="stat-number">{len(parsed)}</div><div class="stat-label">Policies</div></div>
  <div class="stat-box"><div class="stat-number">{total_constraints}</div><div class="stat-label">Constraints</div></div>
  <div class="stat-box eligible"><div class="stat-number">{eligible_count}</div><div class="stat-label">Eligible</div></div>
  <div class="stat-box blocked"><div class="stat-number">{blocked_count}</div><div class="stat-label">Blocked</div></div>
  <div class="stat-box"><div class="stat-number">{len(nodes)}</div><div class="stat-label">Nodes</div></div>
</div>

<div class="card">
  <h2>Interactive Policy Graph</h2>
  <p>Click and drag nodes. Hover for details. Dashed red lines indicate prohibitions.</p>
  <div class="graph-container">
    <div class="graph-main">
      <iframe src="policy_graph.html"></iframe>
    </div>
    <div class="graph-info">
      <h3>About this graph</h3>
      <p>This graph visualizes healthcare policies parsed into structured nodes and edges.</p>
      <h3>Node Types</h3>
      <ul>
        <li><span class="tag" style="background:#3B82F6;color:white">Policy</span> Raw policy text / clause</li>
        <li><span class="tag" style="background:#10B981;color:white">Entity</span> Data, region, org, person</li>
        <li><span class="tag" style="background:#EF4444;color:white">Constraint</span> Rule with value/operator</li>
        <li><span class="tag" style="background:#F59E0B;color:white">Action</span> Transfer, access, process, store</li>
        <li><span class="tag" style="background:#8B5CF6;color:white">Jurisdiction</span> EU, US, India, UK</li>
        <li><span class="tag" style="background:#6366F1;color:white">Compliance</span> HIPAA, GDPR, PCI, FSSAI</li>
        <li><span class="tag" style="background:#DC2626;color:white">Prohibition</span> Forbidden action/transfer</li>
      </ul>
      <h3>How nodes relate</h3>
      <ul>
        <li><code>policy → entity</code> policy applies to</li>
        <li><code>policy → action</code> policy governs</li>
        <li><code>policy → constraint</code> policy requires</li>
        <li><code>policy → prohibition</code> policy forbids</li>
        <li><code>constraint → jurisdiction</code> where rule applies</li>
      </ul>
      <h3>Edge Styles</h3>
      <ul>
        <li>Solid = standard relation</li>
        <li>Dashed red = prohibition</li>
        <li>Thicker = stronger weight</li>
      </ul>
      <h3>Evaluation</h3>
      <p>Each hospital node is scored against parsed constraints. <b>100%</b> means fully compliant; violations reduce score.</p>
    </div>
  </div>
  {legend_html}
</div>

<div class="card">
  <h2>Loaded Policies</h2>
  <p>Obligations, permissions, prohibitions, constraints, and compliance tags extracted from policy text.</p>
  {policy_list_html}
</div>

<div class="card">
  <h2>Node Compliance Evaluation</h2>
  <p>Each federated node evaluated against active policies. Green borders=eligible, red borders=blocked.</p>
  {node_cards_html}
</div>

<div class="card">
  <h2>Compliance Score Chart</h2>
  <iframe src="compliance_scores.html"></iframe>
</div>

<p style="color: #484f58; font-size: 12px; margin-top: 20px;">KAVP v0.1.1 | <a href="https://pypi.org/project/kavp/" style="color:#58a6ff;">PyPI</a> | <a href="https://github.com/Srimzuphd/kavp" style="color:#58a6ff;">GitHub</a></p>
</body></html>"""

    index_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(index_path, "w") as f:
        f.write(index_html)
    print(f"      -> {index_path}")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=OUTPUT_DIR, **kwargs)


def main():
    generate_all()
    ip = get_local_ip()
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"\n{'='*55}")
    print(f"  KAVP Visualization Dashboard")
    print(f"  {'='*55}")
    print(f"  Local:   http://localhost:{PORT}")
    print(f"  Network: http://{ip}:{PORT}")
    print(f"  Press Ctrl+C to stop")
    print(f"{'='*55}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
