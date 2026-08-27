from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from recipe_common import COLORS

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
from src.utils.figure_style import (
    audit_visual_hierarchy,
    figure_size_for_profile,
    palette,
    publication_profile,
    semantic_style,
    validate_final_size,
    validate_figure_layout,
)

_REGISTERED_COLORS = set(palette().values())
HATCHES = ("", "///", "\\\\", "...", "xx", "++")


def new_panel_figure(
    nrows: int,
    ncols: int,
    *,
    height_mm: float = 112.0,
    profile: str = "contest-body",
    sharex: bool | str = False,
    sharey: bool | str = False,
) -> tuple[plt.Figure, np.ndarray]:
    """Create a panel grid directly at its final registered physical size."""
    if nrows < 1 or ncols < 1:
        raise ValueError("Panel grid dimensions must be positive")
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=figure_size_for_profile(profile, height_mm=height_mm),
        sharex=sharex,
        sharey=sharey,
        squeeze=False,
        layout=None,
    )
    return fig, np.asarray(axes, dtype=object)


def print_safe_bar_style(index: int, *, role: str | None = None, color: str | None = None) -> dict[str, object]:
    """Add hatch/edge redundancy without replacing the workspace palette."""
    if index < 0:
        raise ValueError("Bar style index must be non-negative")
    if role is not None and color is not None:
        raise ValueError("Specify either semantic role or registered color")
    if role is not None:
        facecolor = semantic_style(role)["color"]
    elif color is not None:
        if color not in _REGISTERED_COLORS:
            raise ValueError("Bar color must come from config/figure_style.yaml")
        facecolor = color
    else:
        cycle = mpl.rcParams["axes.prop_cycle"].by_key().get("color", [])
        if not cycle:
            raise ValueError("Matplotlib color cycle is empty")
        facecolor = cycle[index % len(cycle)]
    return {
        "facecolor": facecolor,
        "edgecolor": COLORS["ink"],
        "linewidth": 0.55,
        "hatch": HATCHES[index % len(HATCHES)],
    }


def annotate_bars(
    ax: plt.Axes,
    bars: Sequence,
    *,
    indices: Iterable[int] | None = None,
    orientation: str = "vertical",
    fmt: str = "{:.3g}",
    max_labels: int = 8,
    padding_points: float = 2.5,
) -> list:
    """Annotate a deliberately small set of bars; reject label clutter."""
    bar_list = list(bars)
    if orientation not in {"vertical", "horizontal"}:
        raise ValueError("orientation must be vertical or horizontal")
    selected = list(range(len(bar_list))) if indices is None else sorted(set(int(i) for i in indices))
    if len(selected) > max_labels:
        raise ValueError(f"Select at most {max_labels} meaningful bar labels")
    if any(index < 0 or index >= len(bar_list) for index in selected):
        raise IndexError("Bar annotation index is out of range")
    fontsize = float(publication_profile()["direct_label_font_pt"])
    artists = []
    for index in selected:
        bar = bar_list[index]
        if orientation == "vertical":
            value = float(bar.get_height())
            xy = (float(bar.get_x() + bar.get_width() / 2), float(bar.get_y() + bar.get_height()))
            offset = (0, padding_points if value >= 0 else -padding_points)
            ha, va = "center", ("bottom" if value >= 0 else "top")
        else:
            value = float(bar.get_width())
            xy = (float(bar.get_x() + bar.get_width()), float(bar.get_y() + bar.get_height() / 2))
            offset = (padding_points if value >= 0 else -padding_points, 0)
            ha, va = ("left" if value >= 0 else "right"), "center"
        artists.append(
            ax.annotate(
                fmt.format(value),
                xy,
                xytext=offset,
                textcoords="offset points",
                ha=ha,
                va=va,
                fontsize=fontsize,
                color=COLORS["ink"],
                annotation_clip=False,
            )
        )
    return artists


def shared_legend(
    fig: plt.Figure,
    axes: Iterable[plt.Axes],
    *,
    location: str = "top",
    ncols: int | None = None,
    max_entries: int | None = None,
):
    """Create one deduplicated figure-level legend inside reserved canvas space."""
    pairs: list[tuple[object, str]] = []
    seen: set[str] = set()
    for ax in axes:
        handles, labels = ax.get_legend_handles_labels()
        for handle, text in zip(handles, labels, strict=False):
            label_text = str(text)
            if not label_text or label_text.startswith("_") or label_text in seen:
                continue
            seen.add(label_text)
            pairs.append((handle, label_text))
    if not pairs:
        return None
    maximum = int(max_entries or publication_profile()["max_legend_entries"])
    if len(pairs) > maximum:
        raise ValueError("Shared legend is too dense; reduce/direct-label series or explicitly justify a larger maximum")
    handles, labels = zip(*pairs)
    placements = {
        "top": {"loc": "upper center", "bbox_to_anchor": (0.5, 0.985)},
        "right": {"loc": "center right", "bbox_to_anchor": (0.985, 0.5)},
    }
    if location not in placements:
        raise ValueError(f"Unknown shared legend location: {location}")
    return fig.legend(handles, labels, ncols=ncols or min(len(labels), maximum), frameon=False, **placements[location])


def export_publication_triplet(
    fig: plt.Figure,
    output_dir: str | Path,
    stem: str,
    *,
    profile: str = "contest-body",
    margins: tuple[float, float, float, float] = (0.105, 0.965, 0.145, 0.90),
    allow_multiple_primary_axes: bool = False,
) -> list[Path]:
    """Export PDF/SVG/400-dpi PNG while preserving the physical canvas.

    bbox_inches='tight' is intentionally not the default because cropping would
    change the physical PDF/SVG size after the final-size contract has passed.
    """
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    outputs = [target / f"{stem}.pdf", target / f"{stem}.svg", target / f"{stem}.png"]
    left, right, bottom, top = margins
    if not (0 <= left < right <= 1 and 0 <= bottom < top <= 1):
        raise ValueError("Invalid publication margins")
    fig.subplots_adjust(left=left, right=right, bottom=bottom, top=top)
    size = validate_final_size(fig, profile=profile)
    if not size["passed"]:
        raise ValueError(f"Figure size audit failed: {size['errors']}")
    layout = validate_figure_layout(fig, allow_multiple_primary_axes=allow_multiple_primary_axes)
    if not layout["passed"]:
        raise ValueError(f"Figure layout audit failed: {layout['errors']}")
    hierarchy = audit_visual_hierarchy(fig)
    if hierarchy["legend_entries"] > 3:
        raise ValueError(f"Axes-level legend is too dense: {hierarchy}")
    fig.savefig(outputs[0], metadata={"Creator": "math-modeling-workbench", "CreationDate": None, "ModDate": None})
    fig.savefig(outputs[1], metadata={"Creator": "math-modeling-workbench", "Date": None})
    fig.savefig(outputs[2], dpi=400, metadata={"Software": "math-modeling-workbench"})
    plt.close(fig)
    return outputs
