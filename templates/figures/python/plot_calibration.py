from __future__ import annotations

import argparse

import matplotlib.pyplot as plt

from recipe_common import COLORS, boolean_series, configure_style, export_triplet, label, load_verified_csv, new_figure, numeric, safe_legend, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot a single verified calibration chart with a comparable baseline.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="calibration")
    parser.add_argument("--response-label", required=True)
    parser.add_argument("--response-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["series", "predicted_mean", "observed_mean", "ci95_half", "is_baseline"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, ["predicted_mean", "observed_mean", "ci95_half"])
    frame["is_baseline"] = boolean_series(frame["is_baseline"], "is_baseline")
    if (frame["ci95_half"] < 0).any():
        raise ValueError("Calibration confidence intervals must be non-negative")
    low = float(min(frame["predicted_mean"].min(), frame["observed_mean"].min()))
    high = float(max(frame["predicted_mean"].max(), frame["observed_mean"].max()))

    fig, ax = new_figure(height_mm=104)
    for series_name, series in frame.groupby("series", sort=True):
        baseline_values = series["is_baseline"].drop_duplicates()
        if len(baseline_values) != 1:
            raise ValueError(f"Series must have one baseline role: {series_name}")
        is_baseline = bool(baseline_values.iloc[0])
        color = COLORS["baseline"] if is_baseline else COLORS["primary"]
        ax.errorbar(
            series["predicted_mean"],
            series["observed_mean"],
            yerr=series["ci95_half"],
            color=color,
            linestyle="--" if is_baseline else "-",
            marker="s" if is_baseline else "o",
            capsize=2.5,
            label=str(series_name),
        )
    ax.plot([low, high], [low, high], color=COLORS["ink"], linestyle=":", linewidth=1.1, label="理想校准")
    ax.set(
        xlabel=label(f"预测{args.response_label}", args.response_unit),
        ylabel=label(f"观测{args.response_label}", args.response_unit),
        xlim=(low, high),
        ylim=(low, high),
    )
    ax.set_aspect("equal", adjustable="box")
    style_axis(ax)
    safe_legend(ax, location="above", ncols=min(3, frame["series"].nunique() + 1))
    export_triplet(fig, args.output_dir, args.stem, margins=(0.14, 0.90, 0.15, 0.89))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
