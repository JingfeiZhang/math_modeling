from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

from recipe_common import COLORS, boolean_series, configure_style, export_triplet, label, load_verified_csv, new_figure, numeric, safe_legend


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot a compact schedule Gantt chart from formal task assignments.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stem", default="schedule-gantt")
    parser.add_argument("--time-label", default="时间")
    parser.add_argument("--time-unit", required=True)
    args = parser.parse_args()

    configure_style()
    required = ["task", "resource", "start", "end", "is_critical"]
    frame = load_verified_csv(args.input, required)
    numeric(frame, ["start", "end"])
    frame["is_critical"] = boolean_series(frame["is_critical"], "is_critical")
    if (frame["end"] <= frame["start"]).any():
        raise ValueError("Every task must end after it starts")
    if len(frame) > 30:
        raise ValueError("schedule-gantt supports at most 30 tasks; aggregate lower-level tasks before plotting")

    frame = frame.sort_values(["start", "end", "resource", "task"]).reset_index(drop=True)
    y = np.arange(len(frame))
    height_mm = min(150, max(96, 6.3 * len(frame) + 40))
    fig, ax = new_figure(height_mm=height_mm)

    for idx, row in frame.iterrows():
        color = COLORS["risk"] if bool(row["is_critical"]) else COLORS["primary"]
        width = float(row["end"] - row["start"])
        ax.barh(idx, width, left=float(row["start"]), height=0.62, color=color, edgecolor=COLORS["ink"], linewidth=0.4)
        if len(frame) <= 18:
            ax.text(float(row["start"]) + width / 2, idx, str(row["task"]), ha="center", va="center", fontsize=7.6, color=COLORS["background"])

    labels = [f"{resource} · {task}" for resource, task in zip(frame["resource"].astype(str), frame["task"].astype(str))]
    ax.set_yticks(y, labels=labels)
    ax.invert_yaxis()
    ax.set(xlabel=label(args.time_label, args.time_unit), ylabel="资源 · 任务")
    ax.grid(axis="x", color=COLORS["grid"], alpha=0.22, linewidth=0.45)
    handles = [Patch(facecolor=COLORS["primary"], edgecolor=COLORS["ink"], label="普通任务")]
    if frame["is_critical"].any():
        handles.append(Patch(facecolor=COLORS["risk"], edgecolor=COLORS["ink"], label="关键任务"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=len(handles), frameon=False)
    export_triplet(fig, args.output_dir, args.stem, margins=(0.27, 0.97, 0.14, 0.88))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
