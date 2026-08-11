from __future__ import annotations

from pathlib import Path
import sys
from typing import Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
from src.utils.figure_style import (
    audit_visual_hierarchy,
    configure_matplotlib,
    direct_label,
    diverging_colormap,
    figure_size_for_profile,
    palette,
    rasterize_dense_layers,
    safe_legend,
    semantic_style,
    sequential_colormap,
    validate_final_size,
    validate_figure_layout,
)


_PALETTE = palette()
COLORS = {
    "primary": _PALETTE["primary"],
    "baseline": _PALETTE["baseline"],
    "improved": _PALETTE["improved"],
    "highlight": _PALETTE["highlight"],
    "secondary": _PALETTE["baseline"],
    "positive": _PALETTE["improved"],
    "risk": _PALETTE["risk"],
    "neutral": _PALETTE["ink"],
    "light": _PALETTE["fill"],
    "grid": _PALETTE["grid"],
    "fill": _PALETTE["fill"],
    "auxiliary": _PALETTE["auxiliary"],
    "accent": _PALETTE["accent"],
    "ink": _PALETTE["ink"],
    "background": _PALETTE["background"],
}


def configure_style() -> None:
    configure_matplotlib("publication-minimal")
    mpl.rcParams["svg.hashsalt"] = "math-modeling-figure-v1"


def new_figure(*, height_mm: float = 104.0, profile: str = "contest-body") -> tuple[plt.Figure, plt.Axes]:
    """Create one publication canvas at its final physical size."""
    return plt.subplots(figsize=figure_size_for_profile(profile, height_mm=height_mm), layout=None)


def load_verified_csv(path: str | Path, required: Iterable[str]) -> pd.DataFrame:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Evidence table does not exist: {source}")
    frame = pd.read_csv(source)
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"Evidence table is missing columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Evidence table is empty")
    return frame


def numeric(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        values = frame[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"Column contains non-finite values: {column}")


def boolean_series(series: pd.Series, name: str) -> pd.Series:
    if series.dtype == bool:
        return series
    mapped = series.astype(str).str.strip().str.lower().map(
        {"1": True, "0": False, "true": True, "false": False, "yes": True, "no": False}
    )
    if mapped.isna().any():
        raise ValueError(f"Column must contain booleans: {name}")
    return mapped.astype(bool)


def label(variable: str, unit: str) -> str:
    return variable if unit.strip().lower() in {"", "none", "dimensionless"} else f"{variable} ({unit})"


def style_axis(ax: plt.Axes) -> None:
    ax.grid(axis="y", color=COLORS["grid"], alpha=0.20, linewidth=0.45, zorder=0)
    ax.tick_params(direction="out", length=3, width=0.7)


def export_triplet(
    fig: plt.Figure,
    output_dir: str | Path,
    stem: str,
    *,
    profile: str = "contest-body",
    margins: tuple[float, float, float, float] = (0.105, 0.965, 0.145, 0.90),
) -> list[Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    outputs = [target / f"{stem}.pdf", target / f"{stem}.svg", target / f"{stem}.png"]
    left, right, bottom, top = margins
    fig.subplots_adjust(left=left, right=right, bottom=bottom, top=top)
    size = validate_final_size(fig, profile=profile)
    if not size["passed"]:
        raise ValueError(f"Figure size audit failed: {size['errors']}")
    layout = validate_figure_layout(fig, allow_multiple_primary_axes=False)
    if not layout["passed"]:
        raise ValueError(f"Figure layout audit failed: {layout['errors']}")
    hierarchy = audit_visual_hierarchy(fig)
    if hierarchy["legend_entries"] > 3:
        raise ValueError(f"Figure legend is too dense: {hierarchy}")
    fig.savefig(outputs[0], metadata={"Creator": "math-modeling-workbench", "CreationDate": None, "ModDate": None})
    fig.savefig(outputs[1], metadata={"Creator": "math-modeling-workbench", "Date": None})
    fig.savefig(outputs[2], dpi=400, metadata={"Software": "math-modeling-workbench"})
    plt.close(fig)
    return outputs
