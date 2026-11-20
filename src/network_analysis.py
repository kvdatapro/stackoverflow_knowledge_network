import os
import pandas as pd
import networkx as nx

def compute_centralities(graph):
    if graph.number_of_nodes() == 0:
        return pd.DataFrame(columns=[
            "user_id", "display_name", "in_degree", "out_degree", "hub_score", "authority_score"
        ])

    in_degree = nx.in_degree_centrality(graph)
    out_degree = nx.out_degree_centrality(graph)

    #NetworkX nx.hits computes Hubs and Authorities using unweighted structural adjacency
    try:
        hubs, authorities = nx.hits(graph, max_iter=500, normalized=True)
    except Exception:
        hubs = {n: 0.0 for n in graph.nodes()}
        authorities = {n: 0.0 for n in graph.nodes()}

    records = []
    for n in graph.nodes():
        name = graph.nodes[n].get("display_name", f"User_{n}")
        records.append({
            "user_id": n,
            "display_name": name,
            "in_degree": round(in_degree.get(n, 0.0), 4),
            "out_degree": round(out_degree.get(n, 0.0), 4),
            "hub_score": round(hubs.get(n, 0.0), 4),
            "authority_score": round(authorities.get(n, 0.0), 4)
        })

    df = pd.DataFrame(records)
    df = df.sort_values(by=["out_degree", "in_degree"], ascending=False).reset_index(drop=True)
    return df

def interpret_metrics(metrics_df):
    if metrics_df.empty:
        return "Empty network: No metrics to interpret."

    top_in = metrics_df.sort_values(by="in_degree", ascending=False).iloc[0]
    top_out = metrics_df.sort_values(by="out_degree", ascending=False).iloc[0]
    top_hub = metrics_df.sort_values(by="hub_score", ascending=False).iloc[0]
    top_auth = metrics_df.sort_values(by="authority_score", ascending=False).iloc[0]

    interpretation = (
        "=== Network Analysis Interpretation ===\n"
        "[Note: Edges are directed Answerer -> Asker. Metrics reflect network connectivity,\n"
        " activity volume, and structural routing, NOT answer correctness or quality.]\n\n"
        f"1. In-Degree Centrality (Knowledge Recipient / Asker):\n"
        f"   - Highest: {top_in['display_name']} ({top_in['in_degree']:.4f})\n"
        f"   - Interpretation: Received incoming answer edges from the greatest fraction of network peers;\n"
        f"     represents a prominent consumer of community knowledge.\n\n"
        f"2. Out-Degree Centrality (Knowledge Provider / Answerer):\n"
        f"   - Highest: {top_out['display_name']} ({top_out['out_degree']:.4f})\n"
        f"   - Interpretation: Dispatched outgoing answer edges to the widest variety of distinct askers;\n"
        f"     acts as an active knowledge broadcaster across the topic.\n\n"
        f"3. Hub Values (HITS - Unweighted Structural Adjacency):\n"
        f"   - Top Hub: {top_hub['display_name']} ({top_hub['hub_score']:.4f})\n"
        f"   - Interpretation: High hub scores identify prolific answerers who connect to\n"
        f"     multiple prominent questioners throughout the network.\n\n"
        f"4. Authority Values (HITS - Unweighted Structural Adjacency):\n"
        f"   - Top Authority: {top_auth['display_name']} ({top_auth['authority_score']:.4f})\n"
        f"   - Interpretation: High authority nodes represent key questioners who attract answers\n"
        f"     from recognized community hubs (structural information sinks).\n"
    )
    return interpretation

def export_metrics(metrics_df, output_path="data/processed/network_metrics.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    metrics_df.to_csv(output_path, index=False)
    print(f"Exported network metrics to {output_path}")
