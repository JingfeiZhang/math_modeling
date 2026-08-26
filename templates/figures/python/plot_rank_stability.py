from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np

from recipe_common import boolean_series, configure_style, export_triplet, load_verified_csv, new_figure, numeric, sequential_colormap


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot rank stability across ordered perturbation scenarios.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="rank-stability")
    args = parser.parse_args()

    configure_style()
    required = ["scenario", "item", "rank", "is_primary"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, ["rank"])
    frame["is_primary"] = boolean_series(frame["is_primary"], "is_primary")
    if (frame["rank"] < 1).any():
        raise ValueError("Ranks must be positive and start at one")

    scenarios = list(frame["scenario"].astype(str).drop_duplicates())
    items = list(frame["item"].astype(str).drop_duplicates())
    if len(scenarios) > 12 or len(items) > 12:
        raise ValueError("rank-stability supports at most 12 scenarios and 12 items; summarize before plotting")
    if frame.duplicated(["scenario", "item"]).any():
        raise ValueError("Each scenario-item pair must appear exactly once")

    primary_items = frame.groupby(frame["item"].astype(str))["is_primary"].max()
    if primary_items.sum() > 1:
        raise ValueError("At most one item may be marked primary")

    pivot = frame.assign(scenario=frame["scenario"].astype(str), item=frame["item"].astype(str)).pivot(index="item", columns="scenario", values="rank")
    pivot = pivot.reindex(index=items, columns=scenarios)
    if pivot.isna().any().any():
        raise ValueError("Rank matrix must be complete for all items and scenarios")

    matrix = pivot.to_numpy(dtype=float)
    max_rank = max(2.0, float(np.max(matrix)))
    fig, ax = new_figure(height_mm=min(132, max(92, 8 * len(items) + 34)))
    ax.imshow(matrix, aspect="auto", interpolation="nearest", cmap=sequential_colormap(), vmin=1, vmax=max_rank)
    ax.set_xticks(np.arange(len(scenarios)), labels=scenarios, rotation=30, ha="right")
    ylabels = [f"★ {item}" if bool(primary_items.get(item, False)) else item for item in items]
    ax.set_yticks(np.arange(len(items)), labels=ylabels)
    ax.set(xlabel="扰动/情景", ylabel="评价对象")

    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            value = matrix[row, col]
            text_color = "white" if value > 0.58 * max_rank else "black"
            ax.text(col, row, f"{int(value)}", ha="center", va="center", fontsize=8, color=text_color)

    ax.tick_params(length=0)
    export_triplet(fig, args.output_dir, args.stem, margins=(0.20, 0.97, 0.22, 0.95))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
