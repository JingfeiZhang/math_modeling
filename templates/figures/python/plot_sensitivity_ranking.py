from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np

from recipe_common import COLORS, configure_style, export_triplet, load_verified_csv, new_figure, numeric, safe_legend, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot verified first-order and total-effect sensitivity indices.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="sensitivity-ranking")
    args = parser.parse_args()

    configure_style()
    required = ["parameter", "first_order", "first_low", "first_high", "total_effect", "total_low", "total_high"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, required[1:])
    if ((frame["first_low"] > frame["first_order"]) | (frame["first_order"] > frame["first_high"])).any():
        raise ValueError("First-order interval must contain its estimate")
    if ((frame["total_low"] > frame["total_effect"]) | (frame["total_effect"] > frame["total_high"])).any():
        raise ValueError("Total-effect interval must contain its estimate")
    frame = frame.sort_values("total_effect")
    y = np.arange(len(frame))
    total_error = np.vstack([frame["total_effect"] - frame["total_low"], frame["total_high"] - frame["total_effect"]])
    first_error = np.vstack([frame["first_order"] - frame["first_low"], frame["first_high"] - frame["first_order"]])

    height_mm = min(112, max(92, 9 * len(frame) + 34))
    fig, ax = new_figure(height_mm=height_mm)
    ax.barh(y, frame["total_effect"], xerr=total_error, color=COLORS["primary"], edgecolor=COLORS["ink"], linewidth=0.45, height=0.58, capsize=2, label="Total effect")
    ax.errorbar(frame["first_order"], y, xerr=first_error, fmt="^", color=COLORS["improved"], markeredgecolor=COLORS["ink"], markeredgewidth=0.4, capsize=2, linestyle="none", label="First order")
    ax.set_yticks(y, labels=frame["parameter"])
    ax.set(xlabel="Sensitivity index", ylabel="Parameter")
    style_axis(ax)
    safe_legend(ax, location="above", ncols=2)
    export_triplet(fig, args.output_dir, args.stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
