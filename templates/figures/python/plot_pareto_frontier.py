from __future__ import annotations

import argparse

import matplotlib.pyplot as plt

from recipe_common import COLORS, boolean_series, configure_style, direct_label, export_triplet, label, load_verified_csv, new_figure, numeric, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot a verified Pareto frontier, feasibility, recommendation, and baseline.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="pareto-frontier")
    parser.add_argument("--x-label", required=True)
    parser.add_argument("--x-unit", required=True)
    parser.add_argument("--y-label", required=True)
    parser.add_argument("--y-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["objective_x", "objective_y", "is_feasible", "is_pareto", "is_recommended", "baseline_x", "baseline_y"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, ["objective_x", "objective_y", "baseline_x", "baseline_y"])
    for column in ["is_feasible", "is_pareto", "is_recommended"]:
        frame[column] = boolean_series(frame[column], column)
    feasible = frame[frame["is_feasible"]]
    frontier = feasible[feasible["is_pareto"]].sort_values("objective_x")
    recommended = feasible[feasible["is_recommended"]]
    baseline = frame[["baseline_x", "baseline_y"]].drop_duplicates()
    if frontier.empty:
        raise ValueError("No feasible Pareto points were marked in the evidence table")

    fig, ax = new_figure(height_mm=104)
    rejected = frame[~frame["is_feasible"]]
    if not rejected.empty:
        ax.scatter(rejected["objective_x"], rejected["objective_y"], s=12, color=COLORS["grid"], linewidth=0.35, marker="x")
    ax.scatter(feasible["objective_x"], feasible["objective_y"], s=13, facecolor="white", edgecolor=COLORS["baseline"], linewidth=0.55)
    ax.plot(frontier["objective_x"], frontier["objective_y"], color=COLORS["primary"], marker="o", markersize=3.2)
    ax.scatter(baseline["baseline_x"], baseline["baseline_y"], s=42, marker="s", facecolor="white", edgecolor=COLORS["baseline"], linewidth=1.1, zorder=4)
    base = baseline.iloc[0]
    direct_label(ax, float(base["baseline_x"]), float(base["baseline_y"]), "Baseline", role="baseline", offset_points=(6, -7))
    if not recommended.empty:
        point = recommended.iloc[0]
        ax.scatter(recommended["objective_x"], recommended["objective_y"], s=58, facecolor=COLORS["highlight"], edgecolor=COLORS["ink"], marker="D", linewidth=0.7, zorder=5)
        direct_label(ax, float(point["objective_x"]), float(point["objective_y"]), "Recommended", role="optimum_or_threshold", offset_points=(7, 7))
    frontier_label = frontier.iloc[0]
    direct_label(
        ax, float(frontier_label["objective_x"]), float(frontier_label["objective_y"]),
        "Pareto 前沿", role="main_model", offset_points=(-6, 10), ha="right",
        bbox={"facecolor": COLORS["background"], "edgecolor": "none", "alpha": 0.82, "pad": 0.6},
    )
    ax.set(xlabel=label(args.x_label, args.x_unit), ylabel=label(args.y_label, args.y_unit))
    style_axis(ax)
    export_triplet(fig, args.output_dir, args.stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
