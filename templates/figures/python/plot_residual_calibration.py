from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np

from recipe_common import COLORS, configure_style, export_triplet, label, load_verified_csv, numeric, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot calibration and residual diagnostics from verified predictions.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="residual-calibration")
    parser.add_argument("--response-label", required=True)
    parser.add_argument("--response-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["observed", "predicted", "baseline_prediction"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, required)
    residual = frame["observed"] - frame["predicted"]
    low = float(min(frame["observed"].min(), frame["predicted"].min(), frame["baseline_prediction"].min()))
    high = float(max(frame["observed"].max(), frame["predicted"].max(), frame["baseline_prediction"].max()))
    rmse = float(np.sqrt(np.mean(np.square(residual))))
    bias = float(np.mean(residual))

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.05), constrained_layout=True)
    ax = axes[0]
    ax.plot([low, high], [low, high], color=COLORS["neutral"], linestyle=":", label="Ideal")
    ax.scatter(frame["observed"], frame["baseline_prediction"], s=12, facecolor="none", edgecolor=COLORS["secondary"], linewidth=0.7, label="Baseline")
    ax.scatter(frame["observed"], frame["predicted"], s=13, color=COLORS["primary"], alpha=0.75, label="Model")
    ax.set(xlabel=label("Observed", args.response_unit), ylabel=label("Predicted", args.response_unit), title="(a) Calibration")
    style_axis(ax)
    ax.legend()

    ax = axes[1]
    ax.axhline(0, color=COLORS["neutral"], linestyle=":")
    ax.scatter(frame["predicted"], residual, s=13, color=COLORS["primary"], alpha=0.75)
    ax.set(xlabel=label("Fitted value", args.response_unit), ylabel=label("Residual", args.response_unit), title="(b) Residual structure")
    style_axis(ax)
    ax.text(0.03, 0.97, f"RMSE = {rmse:.3g}\nBias = {bias:.3g}", transform=ax.transAxes, va="top")

    export_triplet(fig, args.output_dir, args.stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
