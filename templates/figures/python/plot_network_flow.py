from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.lines import Line2D

from recipe_common import COLORS, configure_style, export_triplet, load_verified_csv, new_figure, numeric


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot verified network flows and changes from baseline.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="network-flow")
    parser.add_argument("--flow-unit", required=True)
    parser.add_argument("--layout-seed", type=int, required=True)
    args = parser.parse_args()

    configure_style()
    required = ["source", "target", "flow", "baseline_flow"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, ["flow", "baseline_flow"])
    graph = nx.from_pandas_edgelist(frame, "source", "target", ["flow", "baseline_flow"], create_using=nx.DiGraph)
    if graph.number_of_edges() == 0:
        raise ValueError("Network evidence contains no edges")
    position = nx.spring_layout(graph, seed=args.layout_seed, weight="flow")
    flows = np.array([graph[u][v]["flow"] for u, v in graph.edges()], dtype=float)
    deltas = np.array([graph[u][v]["flow"] - graph[u][v]["baseline_flow"] for u, v in graph.edges()], dtype=float)
    widths = 0.7 + 3.0 * flows / max(float(np.max(flows)), 1e-12)
    fig, ax = new_figure(height_mm=108)
    nx.draw_networkx_nodes(graph, position, ax=ax, node_size=320, node_color="white", edgecolors=COLORS["primary"], linewidths=1.1)
    nx.draw_networkx_labels(graph, position, ax=ax, font_size=7.5)
    edges = list(graph.edges())
    positive = [index for index, delta in enumerate(deltas) if delta >= 0]
    negative = [index for index, delta in enumerate(deltas) if delta < 0]
    if positive:
        nx.draw_networkx_edges(
            graph, position, ax=ax, edgelist=[edges[index] for index in positive],
            width=[widths[index] for index in positive], edge_color=COLORS["improved"],
            style="solid", arrows=True, arrowsize=10, connectionstyle="arc3,rad=0.05",
        )
    if negative:
        nx.draw_networkx_edges(
            graph, position, ax=ax, edgelist=[edges[index] for index in negative],
            width=[widths[index] for index in negative], edge_color=COLORS["risk"],
            style="dashed", arrows=True, arrowsize=10, connectionstyle="arc3,rad=0.05",
        )
    handles = [
        Line2D([0], [0], color=COLORS["improved"], lw=1.8, linestyle="-", label="高于基线"),
        Line2D([0], [0], color=COLORS["risk"], lw=1.8, linestyle="--", label="低于基线"),
    ]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 1.015), ncols=2, borderaxespad=0)
    ax.set_axis_off()
    export_triplet(fig, args.output_dir, args.stem, margins=(0.04, 0.97, 0.04, 0.89))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
