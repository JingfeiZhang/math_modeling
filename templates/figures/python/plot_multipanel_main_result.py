from __future__ import annotations

import argparse
import math

from publication_helpers import export_publication_triplet, new_panel_figure, shared_legend
from recipe_common import COLORS, configure_style, label, load_verified_csv, numeric, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot coordinated main-result panels from a verified long-form table.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="multipanel-main-result")
    parser.add_argument("--x-label", required=True)
    parser.add_argument("--x-unit", required=True)
    parser.add_argument("--y-label", required=True)
    parser.add_argument("--y-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["panel", "series", "x", "value", "baseline"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, ["x", "value", "baseline"])
    panels = list(dict.fromkeys(frame["panel"].astype(str)))
    if len(panels) > 6:
        raise ValueError("Split figures with more than six panels")
    columns = 2 if len(panels) > 1 else 1
    rows = math.ceil(len(panels) / columns)
    fig, axes = new_panel_figure(rows, columns, height_mm=112, sharex=True)
    palette = [COLORS["primary"], COLORS["secondary"], COLORS["positive"], COLORS["risk"]]
    for panel_index, panel_name in enumerate(panels):
        ax = axes.flat[panel_index]
        subset = frame[frame["panel"].astype(str) == panel_name]
        baseline = subset[["x", "baseline"]].drop_duplicates().sort_values("x")
        ax.plot(baseline["x"], baseline["baseline"], color=COLORS["neutral"], linestyle="--", label="Baseline")
        for series_index, (series_name, series) in enumerate(subset.groupby("series", sort=True)):
            series = series.sort_values("x")
            ax.plot(
                series["x"],
                series["value"],
                color=palette[series_index % len(palette)],
                marker="o",
                markersize=2.5,
                label=str(series_name),
            )
        ax.set_title(f"({chr(97 + panel_index)}) {panel_name}")
        ax.set_ylabel(label(args.y_label, args.y_unit))
        style_axis(ax)
    for empty_index in range(len(panels), rows * columns):
        axes.flat[empty_index].set_visible(False)
    for ax in axes[-1, :]:
        if ax.get_visible():
            ax.set_xlabel(label(args.x_label, args.x_unit))

    visible_axes = [ax for ax in axes.flat if ax.get_visible()]
    # A shared legend avoids repeating the same legend box in every panel.
    # Compatibility figures may contain baseline plus up to four series, so
    # any request above five entries should be split or redesigned.
    shared_legend(fig, visible_axes, location="top", max_entries=5)
    export_publication_triplet(
        fig,
        args.output_dir,
        args.stem,
        margins=(0.10, 0.97, 0.13, 0.86),
        allow_multiple_primary_axes=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
