from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np

from recipe_common import COLORS, configure_style, export_triplet, label, load_verified_csv, new_figure, numeric, safe_legend, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot observed versus predicted values for the primary model and baseline.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="observed-vs-predicted")
    parser.add_argument("--variable-label", required=True)
    parser.add_argument("--variable-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["observed", "predicted", "baseline_prediction"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, required)

    values = frame[required].to_numpy(dtype=float)
    lower = float(np.nanmin(values))
    upper = float(np.nanmax(values))
    span = upper - lower or 1.0
    lower -= 0.04 * span
    upper += 0.04 * span
    point_size = 17 if len(frame) <= 300 else 9
    alpha = 0.82 if len(frame) <= 500 else 0.42

    fig, ax = new_figure(height_mm=104)
    ax.plot([lower, upper], [lower, upper], color=COLORS["ink"], linewidth=0.8, linestyle=":", zorder=1)
    ax.scatter(frame["observed"], frame["baseline_prediction"], s=point_size, facecolor="white", edgecolor=COLORS["baseline"], linewidth=0.65, alpha=alpha, label="Baseline", zorder=2)
    ax.scatter(frame["observed"], frame["predicted"], s=point_size, color=COLORS["primary"], alpha=alpha, label="主模型", zorder=3)
    ax.set_xlim(lower, upper)
    ax.set_ylim(lower, upper)
    axis_label = label(args.variable_label, args.variable_unit)
    ax.set(xlabel=f"观测值：{axis_label}", ylabel=f"预测值：{axis_label}")
    style_axis(ax)
    safe_legend(ax, location="above", ncols=2)
    export_triplet(fig, args.output_dir, args.stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
