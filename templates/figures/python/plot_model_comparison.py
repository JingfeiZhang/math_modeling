from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np

from recipe_common import COLORS, boolean_series, configure_style, export_triplet, label, load_verified_csv, new_figure, numeric, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot model estimates and uncertainty against a comparable baseline.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="model-comparison")
    parser.add_argument("--metric-label", required=True)
    parser.add_argument("--metric-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["model", "estimate", "lower", "upper", "is_baseline", "is_primary"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, ["estimate", "lower", "upper"])
    frame["is_baseline"] = boolean_series(frame["is_baseline"], "is_baseline")
    frame["is_primary"] = boolean_series(frame["is_primary"], "is_primary")
    if ((frame["lower"] > frame["estimate"]) | (frame["estimate"] > frame["upper"])).any():
        raise ValueError("Every uncertainty interval must contain its estimate")
    if frame["is_baseline"].sum() != 1 or frame["is_primary"].sum() != 1:
        raise ValueError("Exactly one baseline and one primary model are required")
    frame = frame.sort_values("estimate")
    y = np.arange(len(frame))
    colors = [COLORS["primary"] if primary else COLORS["baseline"] if baseline else COLORS["ink"] for primary, baseline in zip(frame["is_primary"], frame["is_baseline"])]
    markers = ["o" if primary else "s" if baseline else "D" for primary, baseline in zip(frame["is_primary"], frame["is_baseline"])]

    fig, ax = new_figure(height_mm=min(112, max(92, 10 * len(frame) + 34)))
    for index, (_, row) in enumerate(frame.iterrows()):
        error = np.array([[row["estimate"] - row["lower"]], [row["upper"] - row["estimate"]]])
        ax.errorbar(row["estimate"], index, xerr=error, fmt=markers[index], color=colors[index], markeredgecolor=COLORS["ink"], markeredgewidth=0.45, capsize=2.5, zorder=3)
        ax.annotate(f"{row['estimate']:.3g}", (row["upper"], index), xytext=(6, 0), textcoords="offset points", ha="left", va="center", color=COLORS["ink"], fontsize=8)
    ax.set_yticks(y, labels=frame["model"])
    ax.set(xlabel=label(args.metric_label, args.metric_unit), ylabel="模型")
    style_axis(ax)
    export_triplet(fig, args.output_dir, args.stem, margins=(0.19, 0.92, 0.15, 0.94))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
