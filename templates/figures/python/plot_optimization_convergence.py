from __future__ import annotations

import argparse

import matplotlib.pyplot as plt

from recipe_common import COLORS, configure_style, direct_label, export_triplet, label, load_verified_csv, new_figure, numeric, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot multi-run optimization convergence with a matched baseline.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="optimization-convergence")
    parser.add_argument("--objective-label", required=True)
    parser.add_argument("--objective-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["iteration", "run", "objective", "baseline_objective"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, required)
    if frame.duplicated(["iteration", "run"]).any():
        raise ValueError("Each iteration-run pair must be unique")

    fig, ax = new_figure(height_mm=100)
    for column, color, linestyle, marker, series_label in (
        ("baseline_objective", COLORS["baseline"], "--", "s", "Baseline"),
        ("objective", COLORS["primary"], "-", "o", "Main model"),
    ):
        grouped = frame.groupby("iteration")[column]
        mean = grouped.mean()
        low = grouped.quantile(0.05)
        high = grouped.quantile(0.95)
        ax.fill_between(mean.index, low, high, color=color, alpha=0.14, linewidth=0)
        ax.plot(mean.index, mean, color=color, linestyle=linestyle, marker=marker, markevery=max(1, len(mean) // 10), label=f"_{series_label}")
        role = "baseline" if column == "baseline_objective" else "main_model"
        direct_label(ax, float(mean.index[-1]), float(mean.iloc[-1]), series_label, role=role, offset_points=(6, -5 if role == "baseline" else 5))
    ax.set(xlabel="Iteration", ylabel=label(args.objective_label, args.objective_unit))
    style_axis(ax)
    export_triplet(fig, args.output_dir, args.stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
