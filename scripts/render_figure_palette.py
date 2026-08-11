"""Render a non-evidence preview of the fixed journal-spectrum-v2 palette."""
from __future__ import annotations

from pathlib import Path
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.utils.figure_style import ROOT, configure_matplotlib, palette


def main() -> None:
    configure_matplotlib()
    colors = palette()
    output = ROOT / "output" / "figure_palette_preview"
    output.parent.mkdir(parents=True, exist_ok=True)
    x = np.linspace(0, 1, 100)
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.4), constrained_layout=True)

    ax = axes[0, 0]
    for name in ("primary", "baseline", "improved", "highlight", "risk", "auxiliary"):
        ax.plot(x, 0.4 + 0.08 * np.sin(2 * np.pi * x + len(name)), color=colors[name], label=name)
    ax.set_title("Semantic series")
    ax.legend(ncols=2)

    ax = axes[0, 1]
    ax.plot(x, 0.7 + 0.15 * np.sin(2 * np.pi * x), color=colors["baseline"], linestyle="--", label="Baseline")
    ax.plot(x, 0.72 + 0.15 * np.sin(2 * np.pi * x + 0.1), color=colors["primary"], label="Main model")
    ax.fill_between(x, 0.68 + 0.15 * np.sin(2 * np.pi * x), 0.76 + 0.15 * np.sin(2 * np.pi * x), color=colors["primary"], alpha=0.20)
    ax.set_title("Model / baseline / interval")
    ax.legend()

    ax = axes[0, 2]
    for index, name in enumerate(("primary", "improved", "highlight")):
        ax.plot(x, 1 - 0.2 * (x - 0.5 - index * 0.05) ** 2, color=colors[name], label=name)
    ax.axvline(0.5, color=colors["highlight"], linestyle=":")
    ax.set_title("Sensitivity")
    ax.legend()

    ax = axes[1, 0]
    matrix = np.outer(np.sin(np.linspace(0, 3, 10)), np.cos(np.linspace(0, 3, 12)))
    sequential = mpl.colors.LinearSegmentedColormap.from_list(
        "journal-sequential", [colors["background"], colors["baseline"], colors["primary"]]
    )
    ax.imshow(matrix, cmap=sequential, aspect="auto")
    ax.set_title("Unified sequential")

    ax = axes[1, 1]
    diverging = mpl.colors.LinearSegmentedColormap.from_list(
        "journal-diverging", [colors["primary"], colors["fill"], colors["risk"]]
    )
    ax.imshow(matrix, cmap=diverging, aspect="auto", vmin=-1, vmax=1)
    ax.set_title("Unified diverging")

    ax = axes[1, 2]
    grayscale = np.asarray([[int(colors[name][i : i + 2], 16) for i in (1, 3, 5)] for name in ("primary", "baseline", "improved", "highlight", "risk", "auxiliary")]) / 255
    gray = 0.2126 * grayscale[:, 0] + 0.7152 * grayscale[:, 1] + 0.0722 * grayscale[:, 2]
    ax.barh(range(len(gray)), gray, color=[(value, value, value) for value in gray], edgecolor=colors["ink"])
    ax.set_yticks(range(len(gray)), ("primary", "baseline", "improved", "highlight", "risk", "auxiliary"))
    ax.set_xlim(0, 1)
    ax.set_title("Grayscale preview")

    for ax in axes.flat:
        ax.grid(axis="y", color=colors["grid"], alpha=0.45, linewidth=0.6)
    fig.savefig(output.with_suffix(".pdf"), bbox_inches="tight", metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(output.with_suffix(".svg"), bbox_inches="tight", metadata={"Date": None})
    fig.savefig(output.with_suffix(".png"), dpi=400, bbox_inches="tight", metadata={"Software": "math-modeling-workbench"})
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
