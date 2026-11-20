import os
import matplotlib.pyplot as plt
import networkx as nx

def plot_overall_network(graph, output_path="visualizations/overall_network.png"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(13, 9))

    if graph.number_of_nodes() == 0:
        ax.text(0.5, 0.5, "Empty Network", ha="center", va="center", fontsize=14)
        plt.savefig(output_path, dpi=300)
        plt.close()
        return

    pos = nx.spring_layout(graph, seed=42, k=0.9, iterations=60)

    node_sizes = []
    for n in graph.nodes():
        total_act = graph.nodes[n].get("total_activity", graph.degree(n))
        node_sizes.append(max(250, total_act * 180))

    edges = list(graph.edges(data=True))
    weights = [data.get("weight", 1) for _, _, data in edges]
    edge_widths = [max(1.2, min(w * 1.5, 6.0)) for w in weights]

    nx.draw_networkx_nodes(
        graph, pos, node_size=node_sizes, node_color="#2b5c8f",
        alpha=0.88, edgecolors="#142d47", linewidths=1.5, ax=ax
    )

    nx.draw_networkx_edges(
        graph, pos, width=edge_widths, edge_color="#5c6b73",
        alpha=0.75, arrows=True, arrowsize=14, arrowstyle="->",
        connectionstyle="arc3,rad=0.12", ax=ax
    )

    labels = {n: graph.nodes[n].get("display_name", str(n)) for n in graph.nodes()}
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=8, font_family="sans-serif", ax=ax)

    legend_elements = [
        plt.Line2D([0], [0], marker="o", color="w", label=r"Node Size $\propto$ Total Activity (Questions + Answers)",
                   markerfacecolor="#2b5c8f", markersize=12, markeredgecolor="#142d47"),
        plt.Line2D([0], [0], color="#5c6b73", lw=3.0, label=r"Edge Width $\propto$ Total Answers Exchanged (Answerer $\rightarrow$ Asker)"),
        plt.Line2D([0], [0], marker="s", color="w", label="*Note: Isolated nodes are top-active users whose partners sit outside this 20-node sample",
                   markerfacecolor="none", markersize=0)
    ]
    ax.legend(handles=legend_elements, loc="upper left", frameon=True, fontsize=8.5, framealpha=0.92)

    ax.set_title("StackOverflow User Knowledge Network (Filtered Top-20 Active Users)\nDirected Edges: Answerer $\\rightarrow$ Asker",
                 fontsize=13, fontweight="bold", pad=15)
    ax.axis("off")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved network visualization to {output_path}")

def plot_blooms_subnetworks(graph, output_path="visualizations/blooms_taxonomy_networks.png"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    blooms_levels = ["Remembering", "Understanding", "Applying", "Analyzing", "Evaluating", "Creating"]
    colors = ["#4575b4", "#74add1", "#abd9e9", "#fdae61", "#f46d43", "#d73027"]

    fig, axes = plt.subplots(2, 3, figsize=(16, 11))
    axes = axes.flatten()

    pos = nx.spring_layout(graph, seed=42, k=0.9) if graph.number_of_nodes() > 0 else {}

    for idx, (level, color) in enumerate(zip(blooms_levels, colors)):
        ax = axes[idx]
        subG = nx.DiGraph()

        for n in graph.nodes():
            subG.add_node(n, display_name=graph.nodes[n].get("display_name", str(n)))

        level_edge_weights = []
        for u, v, data in graph.edges(data=True):
            b_dict = data.get("blooms", {})
            count = b_dict.get(level, 0)
            if count > 0:
                subG.add_edge(u, v, weight=count)
                level_edge_weights.append(count)

        pair_count = subG.number_of_edges()
        total_answers_in_level = sum(level_edge_weights)

        nx.draw_networkx_nodes(
            subG, pos, node_size=180, node_color="#e0e0e0",
            alpha=0.75, edgecolors="#999999", linewidths=0.8, ax=ax
        )

        active_nodes = [n for n in subG.nodes() if subG.degree(n) > 0]
        if active_nodes:
            nx.draw_networkx_nodes(
                subG, pos, nodelist=active_nodes, node_size=280,
                node_color=color, alpha=0.9, edgecolors="#333333", linewidths=1.2, ax=ax
            )

        if pair_count > 0:
            widths = [max(1.2, min(w * 1.5, 5.0)) for w in level_edge_weights]
            nx.draw_networkx_edges(
                subG, pos, width=widths, edge_color=color,
                alpha=0.85, arrows=True, arrowsize=10, connectionstyle="arc3,rad=0.1", ax=ax
            )

        ax.set_title(
            f"{level}\n({pair_count} directed pairs | {total_answers_in_level} answers)",
            fontsize=11, fontweight="bold", pad=8
        )
        ax.axis("off")

    fig.suptitle(
        "Answer Interactions Categorized by Bloom's Taxonomy Cognitive Levels\n"
        "[Counts show: Unique Directed User Pairs | Total Underlying Answers Exchanged]",
        fontsize=14, fontweight="bold", y=0.98
    )
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved Bloom's level visualizations to {output_path}")
