from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np

from recipe_common import configure_style, diverging_colormap, export_triplet, label, load_verified_csv, new_figure, numeric


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot scenario-by-metric changes from a comparable baseline.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="robustness-matrix")
    parser.add_argument("--value-label", required=True)
    parser.add_argument("--value-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["scenario", "metric", "value", "baseline"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, ["value", "baseline"])
    if frame.duplicated(["scenario", "metric"]).any():
        raise ValueError("Each scenario-metric pair must be unique")
    frame["delta"] = frame["value"] - frame["baseline"]
    scenario_order = list(dict.fromkeys(frame["scenario"].astype(str)))
    metric_order = list(dict.fromkeys(frame["metric"].astype(str)))
    matrix = frame.pivot(index="scenario", columns="metric", values="delta").reindex(index=scenario_order, columns=metric_order)
    if matrix.isna().any().any():
        raise ValueError("Robustness matrix must be complete; missing scenario-metric cells are not inferred")
    limit = float(np.max(np.abs(matrix.to_numpy())))
    if limit == 0:
        limit = 1.0

    fig, ax = new_figure(height_mm=104)
    image = ax.imshow(matrix.to_numpy(), cmap=diverging_colormap(), vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(len(matrix.columns)), labels=matrix.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(matrix.index)), labels=matrix.index)
    ax.set(xlabel="指标", ylabel="情景")
    for row in range(len(matrix.index)):
        for column in range(len(matrix.columns)):
            value = matrix.iat[row, column]
            ax.text(column, row, f"{value:.3g}", ha="center", va="center", color="white" if abs(value) > 0.55 * limit else "black", fontsize=8)
    colorbar = fig.colorbar(image, ax=ax, shrink=0.88, pad=0.035)
    colorbar.set_label(label(args.value_label, args.value_unit))
    export_triplet(fig, args.output_dir, args.stem, margins=(0.16, 0.88, 0.22, 0.94))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
