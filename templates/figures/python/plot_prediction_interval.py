from __future__ import annotations

import argparse

import matplotlib.pyplot as plt

from recipe_common import COLORS, configure_style, direct_label, export_triplet, label, load_verified_csv, new_figure, numeric, safe_legend, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot observed values, prediction interval, and a comparable baseline.")
    parser.add_argument("--input", required=True, help="CSV evidence table")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="prediction-interval")
    parser.add_argument("--x-label", required=True)
    parser.add_argument("--x-unit", required=True)
    parser.add_argument("--y-label", required=True)
    parser.add_argument("--y-unit", required=True)
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    configure_style()
    required = ["x", "observed", "predicted", "lower", "upper", "baseline"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, required)
    frame = frame.sort_values("x")
    if (frame["lower"] > frame["upper"]).any():
        raise ValueError("Prediction interval has lower values above upper values")

    fig, ax = new_figure(height_mm=100)
    ax.fill_between(frame["x"], frame["lower"], frame["upper"], color=COLORS["primary"], alpha=0.11, linewidth=0, label="95% interval")
    ax.plot(frame["x"], frame["predicted"], color=COLORS["primary"], label="_Model")
    ax.plot(frame["x"], frame["baseline"], color=COLORS["baseline"], linestyle="--", label="_Baseline")
    ax.scatter(frame["x"], frame["observed"], s=11, facecolor="white", edgecolor=COLORS["ink"], linewidth=0.6, label="Observed", zorder=3)
    last = frame.iloc[-1]
    span = float(frame["x"].max() - frame["x"].min()) or 1.0
    ax.set_xlim(float(frame["x"].min()), float(frame["x"].max()) + 0.08 * span)
    direct_label(ax, float(last["x"]), float(last["predicted"]), "Model", role="main_model", offset_points=(5, 5))
    direct_label(ax, float(last["x"]), float(last["baseline"]), "Baseline", role="baseline", offset_points=(5, -5))
    ax.set(xlabel=label(args.x_label, args.x_unit), ylabel=label(args.y_label, args.y_unit))
    style_axis(ax)
    safe_legend(ax, location="above", ncols=2)
    export_triplet(fig, args.output_dir, args.stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
