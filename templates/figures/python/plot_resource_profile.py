from __future__ import annotations

import argparse

import matplotlib.pyplot as plt

from recipe_common import COLORS, configure_style, export_triplet, label, load_verified_csv, new_figure, numeric, safe_legend, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot resource usage, capacity, and baseline usage over an ordered horizon.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="resource-profile")
    parser.add_argument("--x-label", required=True)
    parser.add_argument("--x-unit", required=True)
    parser.add_argument("--resource-label", required=True)
    parser.add_argument("--resource-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["time", "usage", "capacity", "baseline_usage"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, required)
    frame = frame.sort_values("time")
    if (frame["capacity"] < 0).any():
        raise ValueError("Capacity must be non-negative")

    fig, ax = new_figure(height_mm=100)
    ax.plot(frame["time"], frame["usage"], color=COLORS["primary"], linewidth=1.7, label="主方案")
    ax.plot(frame["time"], frame["baseline_usage"], color=COLORS["baseline"], linewidth=1.1, linestyle="--", label="Baseline")
    ax.plot(frame["time"], frame["capacity"], color=COLORS["risk"], linewidth=1.0, linestyle=":", label="容量上限")
    exceed = frame["usage"] > frame["capacity"]
    if exceed.any():
        ax.fill_between(frame["time"], frame["capacity"], frame["usage"], where=exceed, color=COLORS["risk"], alpha=0.13, interpolate=True)

    ax.set(xlabel=label(args.x_label, args.x_unit), ylabel=label(args.resource_label, args.resource_unit))
    style_axis(ax)
    safe_legend(ax, location="above", ncols=3)
    export_triplet(fig, args.output_dir, args.stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
