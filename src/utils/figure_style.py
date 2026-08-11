"""Shared publication-figure style for Python and MATLAB workflows."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[2]
STYLE_PATH = ROOT / "config" / "figure_style.yaml"


def load_style(path: str | Path = STYLE_PATH) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Figure style configuration is missing: {source}")
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Figure style configuration must be a mapping")
    if payload.get("palette_id") != "journal-spectrum-v2":
        raise ValueError("Unsupported figure palette id")
    colors = payload.get("colors")
    if not isinstance(colors, dict) or not colors:
        raise ValueError("Figure style must define colors")
    for name, value in colors.items():
        if not isinstance(value, str) or not value.startswith("#") or len(value) != 7:
            raise ValueError(f"Invalid HEX color for {name}: {value!r}")
        int(value[1:], 16)
    categorical = payload.get("categorical_order")
    if not isinstance(categorical, list) or len(categorical) != 8:
        raise ValueError("Figure style must define exactly eight categorical colors")
    for value in categorical:
        if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
            raise ValueError(f"Invalid categorical HEX color: {value!r}")
        int(value[1:], 16)
    return payload


def palette(path: str | Path = STYLE_PATH) -> dict[str, str]:
    return dict(load_style(path)["colors"])


def rgb01(name: str, path: str | Path = STYLE_PATH) -> tuple[float, float, float]:
    value = palette(path)[name].lstrip("#")
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))


def publication_profile(name: str = "publication-minimal", path: str | Path = STYLE_PATH) -> dict[str, Any]:
    """Return a named publication profile from the shared style contract."""
    config = load_style(path)
    profiles = config.get("profiles", {})
    if name not in profiles:
        raise KeyError(f"Unknown figure style profile: {name}")
    return dict(profiles[name])


def target_size_profile(name: str = "contest-body", path: str | Path = STYLE_PATH) -> dict[str, Any]:
    """Return a physical-size contract for a contest or journal target."""
    config = load_style(path)
    profiles = config.get("size_profiles", {})
    if name not in profiles:
        raise KeyError(f"Unknown figure size profile: {name}")
    profile = dict(profiles[name])
    for key in ("width_mm", "height_min_mm", "height_default_mm", "height_max_mm"):
        if not isinstance(profile.get(key), (int, float)) or float(profile[key]) <= 0:
            raise ValueError(f"Invalid {key} in figure size profile: {name}")
    if not profile["height_min_mm"] <= profile["height_default_mm"] <= profile["height_max_mm"]:
        raise ValueError(f"Invalid height range in figure size profile: {name}")
    profile["name"] = name
    return profile


def configure_matplotlib(profile: str | None = None) -> None:
    """Apply the shared journal defaults and an optional restrained profile."""
    import matplotlib as mpl
    from cycler import cycler

    config = load_style()
    colors = config["colors"]
    style = config["style"]
    selected = publication_profile(profile) if profile else {}
    line_width = float(selected.get("line_width_pt", style["line_width_pt"]))
    marker_size = float(selected.get("marker_size_pt", style["marker_size_pt"]))
    mpl.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": int(style["export"]["png_dpi"]),
            "font.family": "sans-serif",
            "font.sans-serif": list(style["font_family"]),
            "font.size": float(style["font_size_pt"]),
            "axes.titlesize": float(style["font_size_pt"]) + 1,
            "axes.labelsize": float(style["font_size_pt"]),
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": colors["ink"],
            "axes.labelcolor": colors["ink"],
            "xtick.color": colors["ink"],
            "ytick.color": colors["ink"],
            "xtick.labelsize": float(style["font_size_pt"]),
            "ytick.labelsize": float(style["font_size_pt"]),
            "legend.fontsize": max(float(style["min_font_pt"]), float(style["font_size_pt"])),
            "legend.frameon": False,
            "legend.borderaxespad": 0.0,
            "legend.handlelength": 2.0,
            "legend.handletextpad": 0.45,
            "legend.columnspacing": 1.0,
            "lines.linewidth": line_width,
            "lines.markersize": marker_size,
            "axes.grid": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "axes.unicode_minus": False,
            "savefig.facecolor": colors["background"],
            "savefig.edgecolor": colors["background"],
            "figure.facecolor": colors["background"],
            "axes.facecolor": colors["background"],
            "axes.prop_cycle": cycler(color=list(config["categorical_order"])),
        }
    )


def audit_visual_hierarchy(fig, profile: str = "publication-minimal") -> dict[str, Any]:
    """Report visual-weight signals that geometric overlap checks cannot detect."""
    from matplotlib.collections import PathCollection, PolyCollection

    selected = publication_profile(profile)
    legend_entries = sum(len(axis.get_legend().get_texts()) for axis in fig.axes if axis.get_legend() is not None)
    visible_gridlines = sum(
        1
        for axis in fig.axes
        for line in [*axis.get_xgridlines(), *axis.get_ygridlines()]
        if line.get_visible() and line.get_alpha() not in (0, 0.0)
    )
    marker_points = 0
    filled_regions = 0
    for axis in fig.axes:
        for line in axis.lines:
            if line.get_marker() not in (None, "None", "", " "):
                marker_points += len(line.get_xdata(orig=False))
        for collection in axis.collections:
            if isinstance(collection, PathCollection):
                marker_points += len(collection.get_offsets())
            if isinstance(collection, PolyCollection):
                filled_regions += 1
    warnings: list[dict[str, Any]] = []
    if legend_entries > int(selected["max_legend_entries"]):
        warnings.append({"code": "LEGEND_VISUAL_WEIGHT", "entries": legend_entries})
    if visible_gridlines > 16:
        warnings.append({"code": "GRID_VISUAL_WEIGHT", "visible_gridlines": visible_gridlines})
    if marker_points > 450:
        warnings.append({"code": "MARKER_DENSITY", "marker_points": marker_points})
    if filled_regions > 5:
        warnings.append({"code": "FILLED_REGION_WEIGHT", "filled_regions": filled_regions})
    return {
        "profile": profile,
        "legend_entries": legend_entries,
        "visible_gridlines": visible_gridlines,
        "marker_points": marker_points,
        "filled_regions": filled_regions,
        "warnings": warnings,
    }


def mm_to_inches(value_mm: float) -> float:
    """Convert a physical figure dimension from millimetres to inches."""
    if value_mm <= 0:
        raise ValueError("Figure dimensions must be positive")
    return float(value_mm) / 25.4


def figure_size(width_mm: float = 158.0, height_mm: float = 104.0) -> tuple[float, float]:
    """Return a Matplotlib size that preserves the requested publication size."""
    return mm_to_inches(width_mm), mm_to_inches(height_mm)


def figure_size_for_profile(
    name: str = "contest-body",
    *,
    height_mm: float | None = None,
    path: str | Path = STYLE_PATH,
) -> tuple[float, float]:
    """Return the exact Matplotlib size for a registered physical target."""
    profile = target_size_profile(name, path)
    height = float(profile["height_default_mm"] if height_mm is None else height_mm)
    if not float(profile["height_min_mm"]) <= height <= float(profile["height_max_mm"]):
        raise ValueError(
            f"Height {height:g} mm is outside {name}'s "
            f"{profile['height_min_mm']:g}-{profile['height_max_mm']:g} mm range"
        )
    return figure_size(float(profile["width_mm"]), height)


def registered_colormap(
    roles: Iterable[str],
    *,
    name: str = "journal-spectrum-v2-derived",
    path: str | Path = STYLE_PATH,
):
    """Build a continuous map using only stops registered in the shared palette."""
    from matplotlib.colors import LinearSegmentedColormap

    colors = palette(path)
    role_list = list(roles)
    if len(role_list) < 2:
        raise ValueError("A registered colormap requires at least two color roles")
    missing = [role for role in role_list if role not in colors]
    if missing:
        raise KeyError(f"Unknown figure color roles: {', '.join(missing)}")
    return LinearSegmentedColormap.from_list(name, [colors[role] for role in role_list])


def sequential_colormap(path: str | Path = STYLE_PATH):
    config = load_style(path)
    return registered_colormap(config["continuous"]["sequential"], name="journal-spectrum-v2-sequential", path=path)


def diverging_colormap(path: str | Path = STYLE_PATH):
    config = load_style(path)
    return registered_colormap(config["continuous"]["diverging"], name="journal-spectrum-v2-diverging", path=path)


def semantic_style(role: str, path: str | Path = STYLE_PATH) -> dict[str, Any]:
    """Resolve one semantic series role to Matplotlib-compatible styling."""
    config = load_style(path)
    mapping = config.get("semantic_roles", {})
    if role not in mapping:
        raise KeyError(f"Unknown semantic figure role: {role}")
    value = dict(mapping[role])
    value["color"] = config["colors"][value["color"]]
    if "line_style" in value:
        value["linestyle"] = value.pop("line_style")
    return value


def direct_label(
    ax,
    x: float,
    y: float,
    text: str,
    *,
    role: str,
    offset_points: tuple[float, float] = (5.0, 0.0),
    path: str | Path = STYLE_PATH,
    **kwargs: Any,
):
    """Add a semantic direct label without introducing an internal legend."""
    config = load_style(path)
    profile = publication_profile(path=path)
    color = semantic_style(role, path)["color"]
    defaults = {
        "xytext": offset_points,
        "textcoords": "offset points",
        "ha": "left" if offset_points[0] >= 0 else "right",
        "va": "center",
        "fontsize": max(float(config["style"]["min_font_pt"]), float(profile["direct_label_font_pt"])),
        "color": color,
        "annotation_clip": False,
    }
    defaults.update(kwargs)
    return ax.annotate(text, (x, y), **defaults)


def safe_legend(ax, *, location: str = "above", ncols: int | None = None, **kwargs: Any):
    """Place a small legend in reserved space instead of on top of evidence."""
    handles, labels = ax.get_legend_handles_labels()
    if not handles:
        return None
    maximum = int(publication_profile()["max_legend_entries"])
    if len(handles) > maximum:
        raise ValueError(f"Legend has {len(handles)} entries; direct-label, highlight, or split the figure")
    columns = ncols or min(len(handles), maximum)
    placements = {
        "above": {"loc": "lower left", "bbox_to_anchor": (0.0, 1.02)},
        "right": {"loc": "upper left", "bbox_to_anchor": (1.02, 1.0)},
    }
    if location not in placements:
        raise ValueError(f"Unknown safe legend location: {location}")
    options = {**placements[location], "ncols": columns, "borderaxespad": 0.0}
    options.update(kwargs)
    return ax.legend(handles, labels, **options)


def rasterize_dense_layers(ax, *, threshold: int | None = None, path: str | Path = STYLE_PATH) -> list[str]:
    """Rasterize only dense data layers while preserving labels and axes as vectors."""
    from matplotlib.collections import PathCollection, QuadMesh

    config = load_style(path)
    minimum = int(threshold or config["rules"]["dense_layer_rasterize_threshold"])
    changed: list[str] = []
    for index, collection in enumerate(ax.collections):
        points = 0
        if isinstance(collection, PathCollection):
            points = len(collection.get_offsets())
        elif isinstance(collection, QuadMesh):
            coordinates = collection.get_coordinates()
            points = int(coordinates.shape[0] * coordinates.shape[1]) if coordinates.ndim >= 2 else len(coordinates)
        if points >= minimum:
            collection.set_rasterized(True)
            changed.append(f"collection-{index}:{points}")
    return changed


def validate_final_size(
    fig,
    *,
    profile: str = "contest-body",
    tolerance_mm: float = 0.6,
    path: str | Path = STYLE_PATH,
) -> dict[str, Any]:
    """Verify the canvas was created at the final physical size, not resized later."""
    target = target_size_profile(profile, path)
    width_in, height_in = fig.get_size_inches()
    width_mm, height_mm = float(width_in) * 25.4, float(height_in) * 25.4
    errors: list[dict[str, Any]] = []
    if abs(width_mm - float(target["width_mm"])) > tolerance_mm:
        errors.append({"code": "PHYSICAL_WIDTH", "actual_mm": round(width_mm, 3), "expected_mm": target["width_mm"]})
    if not float(target["height_min_mm"]) - tolerance_mm <= height_mm <= float(target["height_max_mm"]) + tolerance_mm:
        errors.append({
            "code": "PHYSICAL_HEIGHT",
            "actual_mm": round(height_mm, 3),
            "expected_range_mm": [target["height_min_mm"], target["height_max_mm"]],
        })
    return {"profile": profile, "width_mm": round(width_mm, 3), "height_mm": round(height_mm, 3), "passed": not errors, "errors": errors}


def validate_figure_layout(
    fig,
    *,
    overlap_threshold: float = 0.18,
    allow_multiple_primary_axes: bool = True,
) -> dict[str, Any]:
    """Check text clipping and material text overlap before publication export."""
    from matplotlib.text import Text

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    figure_box = fig.bbox
    text_rows: list[tuple[Text, Any]] = []
    errors: list[dict[str, Any]] = []
    ignored_text = {"", " ", "−", "-"}
    tick_ids = {
        id(label)
        for axes in fig.axes
        for label in [*axes.get_xticklabels(), *axes.get_yticklabels()]
    }
    primary_axes = [axis for axis in fig.axes if axis.get_visible() and axis.get_label() != "<colorbar>"]
    if not allow_multiple_primary_axes and len(primary_axes) != 1:
        errors.append({"code": "PRIMARY_AXES_COUNT", "count": len(primary_axes), "expected": 1})
    for artist in fig.findobj(match=Text):
        if not artist.get_visible() or artist.get_text() in ignored_text:
            continue
        box = artist.get_window_extent(renderer=renderer)
        if box.width <= 0 or box.height <= 0:
            continue
        text_rows.append((artist, box))
        tolerance = 8.0 if id(artist) in tick_ids else 1.5
        if id(artist) not in tick_ids and (
            box.x0 < figure_box.x0 - tolerance
            or box.y0 < figure_box.y0 - tolerance
            or box.x1 > figure_box.x1 + tolerance
            or box.y1 > figure_box.y1 + tolerance
        ):
            errors.append({"code": "TEXT_OUTSIDE_CANVAS", "text": artist.get_text()[:80]})

    overlaps: list[dict[str, Any]] = []
    for left_index, (left_artist, left_box) in enumerate(text_rows):
        for right_artist, right_box in text_rows[left_index + 1 :]:
            if left_artist.axes is not right_artist.axes:
                continue
            width = max(0.0, min(left_box.x1, right_box.x1) - max(left_box.x0, right_box.x0))
            height = max(0.0, min(left_box.y1, right_box.y1) - max(left_box.y0, right_box.y0))
            intersection = width * height
            smaller = min(left_box.width * left_box.height, right_box.width * right_box.height)
            if smaller > 0 and intersection / smaller > overlap_threshold:
                overlaps.append(
                    {
                        "left": left_artist.get_text()[:80],
                        "right": right_artist.get_text()[:80],
                        "overlap_ratio": round(intersection / smaller, 4),
                    }
                )
    if overlaps:
        errors.append({"code": "TEXT_OVERLAP", "count": len(overlaps), "examples": overlaps[:10]})
    return {
        "schema_version": 1,
        "passed": not errors,
        "primary_axes_count": len(primary_axes),
        "text_artist_count": len(text_rows),
        "errors": errors,
    }


def validate_grayscale(path: str | Path = STYLE_PATH) -> dict[str, Any]:
    """Check semantic colors retain enough luminance separation in grayscale."""
    config = load_style(path)
    colors = config["colors"]
    threshold = float(config["rules"]["grayscale_min_luminance_delta"])

    def luminance(value: str) -> float:
        rgb = [int(value[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]

    pairs = [tuple(pair) for pair in config["rules"].get("grayscale_pairs", [])]
    checks = []
    for left, right in pairs:
        delta = abs(luminance(colors[left]) - luminance(colors[right]))
        checks.append({"left": left, "right": right, "luminance_delta": round(delta, 4), "passed": delta >= threshold})
    return {"threshold": threshold, "checks": checks, "passed": all(item["passed"] for item in checks)}
