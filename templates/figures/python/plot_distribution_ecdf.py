from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np

from recipe_common import COLORS, boolean_series, configure_style, export_triplet, label, load_verified_csv, new_figure, numeric, safe_legend, style_axis


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot empirical cumulative distributions for up to three comparable groups.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="distribution-ecdf")
    parser.add_argument("--value-label", required=True)
    parser.add_argument("--value-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["group", "value", "is_baseline", "is_primary"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, ["value"])
    frame["is_baseline"] = boolean_series(frame["is_baseline"], "is_baseline")
    frame["is_primary"] = boolean_series(frame["is_primary"], "is_primary")
    groups = list(frame["group"].astype(str).drop_duplicates())
    if len(groups) < 2 or len(groups) > 3:
        raise ValueError("distribution-ecdf requires two or three comparable groups")

    role_by_group: dict[str, tuple[bool, bool]] = {}
    for group, subset in frame.groupby(frame["group"].astype(str), sort=False):
        baseline_values = subset["is_baseline"].unique()
        primary_values = subset["is_primary"].unique()
        if len(baseline_values) != 1 or len(primary_values) != 1:
            raise ValueError(f"Role flags must be constant within group: {group}")
        role_by_group[str(group)] = (bool(baseline_values[0]), bool(primary_values[0]))
    if sum(role[0] for role in role_by_group.values()) != 1 or sum(role[1] for role in role_by_group.values()) != 1:
        raise ValueError("Exactly one baseline group and one primary group are required")

    fig, ax = new_figure(height_mm=98)
    for group in groups:
        subset = frame[frame["group"].astype(str) == group]
        values = np.sort(subset["value"].to_numpy(dtype=float))
        y = np.arange(1, len(values) + 1, dtype=float) / len(values)
        is_baseline, is_primary = role_by_group[group]
        color = COLORS["primary"] if is_primary else COLORS["baseline"] if is_baseline else COLORS["ink"]
        linestyle = "-" if is_primary else "--" if is_baseline else "-."
        linewidth = 1.7 if is_primary else 1.2
        ax.step(values, y, where="post", color=color, linestyle=linestyle, linewidth=linewidth, label=group)

    ax.set(xlabel=label(args.value_label, args.value_unit), ylabel="经验累积分布")
    ax.set_ylim(0, 1.02)
    style_axis(ax)
    safe_legend(ax, location="above", ncols=len(groups))
    export_triplet(fig, args.output_dir, args.stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
