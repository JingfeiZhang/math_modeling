from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np

from recipe_common import COLORS, configure_style, export_triplet, label, load_verified_csv, new_figure, numeric, safe_legend, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot primary-model and baseline error by group.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="error-by-group")
    parser.add_argument("--metric-label", required=True)
    parser.add_argument("--metric-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["group", "model_error", "baseline_error", "n"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, ["model_error", "baseline_error", "n"])
    if (frame["n"] <= 0).any():
        raise ValueError("Group sample sizes must be positive")
    if frame["group"].astype(str).duplicated().any():
        raise ValueError("Each group must appear exactly once")
    if len(frame) > 20:
        raise ValueError("error-by-group supports at most 20 groups; aggregate or select decision-relevant groups")

    frame = frame.assign(delta=frame["model_error"] - frame["baseline_error"]).sort_values("delta")
    y = np.arange(len(frame))
    fig, ax = new_figure(height_mm=min(130, max(88, 8 * len(frame) + 34)))
    ax.hlines(y, frame["baseline_error"], frame["model_error"], color=COLORS["grid"], linewidth=1.4, zorder=1)
    ax.scatter(frame["baseline_error"], y, marker="s", s=27, facecolor="white", edgecolor=COLORS["baseline"], linewidth=0.8, label="Baseline", zorder=2)
    ax.scatter(frame["model_error"], y, marker="o", s=29, color=COLORS["primary"], label="主模型", zorder=3)
    ax.set_yticks(y, labels=[f"{g} (n={int(n)})" for g, n in zip(frame["group"].astype(str), frame["n"])])
    ax.set(xlabel=label(args.metric_label, args.metric_unit), ylabel="分组")
    style_axis(ax)
    safe_legend(ax, location="above", ncols=2)
    export_triplet(fig, args.output_dir, args.stem, margins=(0.24, 0.96, 0.15, 0.90))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
