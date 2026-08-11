from __future__ import annotations

import argparse

import matplotlib.pyplot as plt

from recipe_common import COLORS, boolean_series, configure_style, export_triplet, figure_size, label, load_verified_csv, numeric, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot one verified residual-scale profile against a comparable baseline.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="residual-diagnostics")
    parser.add_argument("--response-label", required=True)
    parser.add_argument("--response-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["series", "fitted_mean", "rmse", "ci_low", "ci_high", "is_baseline"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, ["fitted_mean", "rmse", "ci_low", "ci_high"])
    frame["is_baseline"] = boolean_series(frame["is_baseline"], "is_baseline")
    if ((frame["ci_low"] > frame["rmse"]) | (frame["rmse"] > frame["ci_high"])).any():
        raise ValueError("Residual interval must contain the RMSE estimate")

    fig, ax = plt.subplots(figsize=figure_size(145, 86), layout="constrained")
    for series_name, series in frame.groupby("series", sort=True):
        series = series.sort_values("fitted_mean")
        baseline_values = series["is_baseline"].drop_duplicates()
        if len(baseline_values) != 1:
            raise ValueError(f"Series must have one baseline role: {series_name}")
        is_baseline = bool(baseline_values.iloc[0])
        color = COLORS["baseline"] if is_baseline else COLORS["primary"]
        ax.fill_between(series["fitted_mean"], series["ci_low"], series["ci_high"], color=color, alpha=0.14, linewidth=0)
        ax.plot(series["fitted_mean"], series["rmse"], color=color, linestyle="--" if is_baseline else "-", marker="s" if is_baseline else "o", label=str(series_name))
    ax.set(
        xlabel=label(f"Fitted {args.response_label}", args.response_unit),
        ylabel=label("Residual RMSE", args.response_unit),
    )
    style_axis(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.015), ncols=min(3, frame["series"].nunique()))
    export_triplet(fig, args.output_dir, args.stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

