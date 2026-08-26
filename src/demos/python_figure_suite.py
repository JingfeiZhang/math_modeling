"""Generate ten deterministic, single-conclusion Python publication figures."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.figure_style import (  # noqa: E402
    audit_visual_hierarchy,
    configure_matplotlib,
    diverging_colormap,
    figure_size,
    load_style,
    palette,
    publication_profile,
    semantic_style,
    sequential_colormap,
    validate_figure_layout,
)
from src.utils.hash_figure_artifacts import build_manifest  # noqa: E402


PALETTE = palette()
STYLE = load_style()
PROFILE = publication_profile()
WIDTH_MM = 180.0


@dataclass(frozen=True)
class DemoSpec:
    demo_id: str
    stem: str
    core_conclusion: str
    archetype: str
    height_mm: float
    axes: list[dict[str, str]]
    baseline: str
    statistics: list[str]
    review_risks: list[str]
    color_encoding: list[dict[str, str]]
    generator: Callable[[Path, np.random.Generator, int], tuple[plt.Figure, dict, list[Path], list[str]]]


def _json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _save_csv(frame: pd.DataFrame, path: Path) -> Path:
    frame.to_csv(path, index=False, encoding="utf-8", float_format="%.10g", lineterminator="\n")
    return path


def _new_figure(height_mm: float, *, width_mm: float = WIDTH_MM) -> tuple[plt.Figure, plt.Axes]:
    """Create a spacious standalone figure; width can be narrowed for equal-aspect plots."""
    fig, ax = plt.subplots(figsize=figure_size(width_mm, height_mm), layout=None)
    return fig, ax


def _style_axis(ax: plt.Axes, *, grid_axis: str | None = None) -> None:
    ax.grid(False)
    if grid_axis:
        ax.grid(
            axis=grid_axis,
            color=PALETTE["grid"],
            alpha=float(PROFILE["grid_alpha"]),
            linewidth=float(PROFILE["grid_line_width_pt"]),
            zorder=0,
        )
    ax.tick_params(direction="out", length=2.8, width=0.65, pad=3)
    ax.margins(x=0.02, y=0.05)


def _legend_above(ax: plt.Axes, *, ncols: int = 2) -> None:
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0.0, 1.015),
        ncols=ncols,
        columnspacing=1.2,
        handlelength=2.3,
        handletextpad=0.5,
        borderaxespad=0.0,
    )


def _direct_label(
    ax: plt.Axes,
    x: float,
    y: float,
    text: str,
    color: str,
    *,
    dx: float = 5.0,
    dy: float = 0.0,
    ha: str = "left",
    background: bool = False,
) -> None:
    box = {"facecolor": PALETTE["background"], "edgecolor": "none", "alpha": 0.84, "pad": 0.8} if background else None
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(dx, dy),
        textcoords="offset points",
        ha=ha,
        va="center",
        color=color,
        fontsize=float(PROFILE["direct_label_font_pt"]),
        annotation_clip=True,
        bbox=box,
    )


def _export(fig: plt.Figure, folder: Path, stem: str) -> dict:
    fig.tight_layout(rect=[0.055, 0.075, 0.98, 0.96], pad=1.0)
    layout = validate_figure_layout(fig)
    layout["visual_hierarchy"] = audit_visual_hierarchy(fig)
    auxiliary_axes = [axis for axis in fig.axes[1:] if axis.get_label() == "<colorbar>"]
    layout.update(
        {
            "primary_axes_count": 1 if fig.axes else 0,
            "auxiliary_axes_count": len(auxiliary_axes),
            "figure_axes_count": len(fig.axes),
            "figure_size_mm": [round(fig.get_figwidth() * 25.4, 3), round(fig.get_figheight() * 25.4, 3)],
        }
    )
    unexpected_axes = len(fig.axes) - (1 + len(auxiliary_axes))
    if not fig.axes or unexpected_axes > 0 or len(auxiliary_axes) > 1:
        layout["passed"] = False
        layout["errors"].append(
            {
                "code": "MULTIPLE_PRIMARY_AXES",
                "figure_axes_count": len(fig.axes),
                "auxiliary_axes_count": len(auxiliary_axes),
            }
        )
    _json(folder / "layout_audit.json", layout)
    if not layout["passed"]:
        raise RuntimeError(f"Pre-export layout audit failed for {stem}: {layout['errors']}")
    outputs = {
        "pdf": folder / f"{stem}.pdf",
        "svg": folder / f"{stem}.svg",
        "png": folder / f"{stem}.png",
    }
    fig.savefig(
        outputs["pdf"],
        metadata={"Creator": "math-modeling-workbench", "CreationDate": None, "ModDate": None},
    )
    fig.savefig(outputs["svg"], metadata={"Creator": "math-modeling-workbench", "Date": None})
    fig.savefig(
        outputs["png"],
        dpi=int(STYLE["style"]["export"]["png_dpi"]),
        metadata={"Software": "math-modeling-workbench"},
    )
    plt.close(fig)
    return {key: str(path.name) for key, path in outputs.items()}


def _finish_demo(folder: Path, spec: DemoSpec, seed: int, fig: plt.Figure, summary: dict, source_files: list[Path], fields: list[str]) -> dict:
    final_width_mm = round(fig.get_figwidth() * 25.4, 3)
    final_height_mm = round(fig.get_figheight() * 25.4, 3)
    summary_payload = {
        "schema_version": 1,
        "synthetic_fixture": True,
        "contest_evidence_eligible": False,
        "seed": seed,
        "source_script": "src/demos/python_figure_suite.py",
        **summary,
    }
    _json(folder / "summary.json", summary_payload)
    exports = _export(fig, folder, spec.stem)
    evidence_chain = [
        {"locator": path.name, "sha256": _sha256(path), "fields": fields}
        for path in source_files
    ]
    contract = {
        "contract_version": "2.0-demo",
        "id": spec.demo_id,
        "question_id": "synthetic-fixture",
        "claim_id": f"fixture-{spec.stem}",
        "core_conclusion": spec.core_conclusion,
        "evidence_chain": evidence_chain,
        "synthetic_fixture": True,
        "contest_evidence_eligible": False,
        "kind": "data",
        "archetype": spec.archetype,
        "backend": "python",
        "palette_id": "journal-spectrum-v2",
        "source_data": [path.name for path in source_files],
        "source_script": "src/demos/python_figure_suite.py",
        "outputs": {**exports, "png_dpi": 400},
        "baseline": spec.baseline,
        "axes": spec.axes,
        "caption": spec.core_conclusion,
        "panel_map": [{"panel": "main", "role": spec.archetype, "subclaim": spec.core_conclusion}],
        "statistics": spec.statistics,
        "review_risks": spec.review_risks,
        "final_width_mm": final_width_mm,
        "final_height_mm": final_height_mm,
        "min_font_pt": 8,
        "color_encoding": spec.color_encoding,
    }
    _json(folder / "demo_contract.json", contract)
    tracked = [*source_files, folder / "summary.json", folder / "demo_contract.json", folder / "layout_audit.json"]
    _json(
        folder / "data_hashes.json",
        {
            "schema_version": 1,
            "files": [{"path": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)} for path in tracked],
        },
    )
    artifact_manifest = build_manifest(folder, spec.stem)
    _json(folder / "artifact_hashes.json", artifact_manifest)
    return {"id": spec.demo_id, "stem": spec.stem, "folder": folder.name, "summary": summary_payload}


def _prediction_data(rng: np.random.Generator) -> pd.DataFrame:
    count = 120
    hour = np.arange(count, dtype=float)
    truth = 610 + 0.42 * hour + 62 * np.sin(2 * np.pi * (hour - 7) / 24) + 18 * np.sin(2 * np.pi * hour / 168)
    noise_scale = 12 + 0.035 * np.maximum(truth - 600, 0)
    observed = truth + rng.normal(0, noise_scale)
    predicted = truth + 2.0 * np.sin(2 * np.pi * hour / 48) + rng.normal(0, 5.0, count)
    baseline = 600 + 0.30 * hour + 51 * np.sin(2 * np.pi * (hour - 5) / 24)
    interval_half = 1.96 * np.sqrt(noise_scale**2 + 25)
    start = datetime(2026, 8, 1)
    return pd.DataFrame(
        {
            "timestamp": [(start + timedelta(hours=int(value))).isoformat(timespec="minutes") for value in hour],
            "hour": hour.astype(int),
            "observed_mw": observed,
            "predicted_mw": predicted,
            "lower_95_mw": predicted - interval_half,
            "upper_95_mw": predicted + interval_half,
            "baseline_mw": baseline,
        }
    )


def _prediction_interval(folder: Path, rng: np.random.Generator, seed: int):
    frame = _prediction_data(rng)
    path = _save_csv(frame, folder / "prediction_series.csv")
    x = pd.to_datetime(frame["timestamp"]).to_numpy()
    observed = frame["observed_mw"].to_numpy()
    predicted = frame["predicted_mw"].to_numpy()
    baseline = frame["baseline_mw"].to_numpy()
    lower = frame["lower_95_mw"].to_numpy()
    upper = frame["upper_95_mw"].to_numpy()
    rmse = float(np.sqrt(np.mean((observed - predicted) ** 2)))
    baseline_rmse = float(np.sqrt(np.mean((observed - baseline) ** 2)))
    coverage = float(np.mean((observed >= lower) & (observed <= upper)))
    fig, ax = _new_figure(112)
    ax.fill_between(x, lower, upper, color=PALETTE["primary"], alpha=float(PROFILE["confidence_band_alpha"]), linewidth=0, zorder=1)
    ax.plot(x, baseline, color=PALETTE["baseline"], linestyle="--", linewidth=1.05, alpha=0.92, zorder=2)
    ax.plot(x, predicted, color=PALETTE["primary"], linestyle="-", linewidth=1.55, zorder=3)
    ax.scatter(x[::6], observed[::6], s=11, facecolor="white", edgecolor=PALETTE["ink"], linewidth=0.55, zorder=4)
    ax.set_xlabel("测试时段")
    ax.set_ylabel("系统负荷 (MW)")
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    _style_axis(ax, grid_axis="y")
    ax.set_xlim(x[0] - np.timedelta64(4, "h"), x[-1] + np.timedelta64(8, "h"))
    _direct_label(ax, x[-1], predicted[-1], "主模型", PALETTE["ink"], dy=13)
    _direct_label(ax, x[-1], baseline[-1], "季节基线", PALETTE["ink"], dy=-13)
    label_index = 96
    _direct_label(ax, x[label_index], upper[label_index], "95% 预测区间", PALETTE["ink"], dx=4, dy=8)
    reduction = 1 - rmse / baseline_rmse
    ax.text(
        0.015,
        0.965,
        f"RMSE 降低 {reduction:.0%}；区间覆盖率 {coverage:.1%}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        color=PALETTE["ink"],
        fontsize=8,
    )
    return fig, {"rmse_mw": rmse, "baseline_rmse_mw": baseline_rmse, "interval_coverage": coverage, "n": len(frame)}, [path], ["observed_mw", "predicted_mw", "lower_95_mw", "upper_95_mw", "baseline_mw"]


def _calibration(folder: Path, rng: np.random.Generator, seed: int):
    frame = _prediction_data(rng)
    path = _save_csv(frame, folder / "calibration_samples.csv")
    observed = frame["observed_mw"].to_numpy()
    predictions = {"主模型": frame["predicted_mw"].to_numpy(), "季节基线": frame["baseline_mw"].to_numpy()}
    fig, ax = _new_figure(126, width_mm=165.0)
    styles = {"主模型": semantic_style("main_model"), "季节基线": semantic_style("baseline")}
    rows = []
    for label, values in predictions.items():
        quantiles = np.quantile(values, np.linspace(0, 1, 11))
        bins = np.unique(quantiles)
        bin_id = np.clip(np.digitize(values, bins[1:-1]), 0, len(bins) - 2)
        centers, means, errors = [], [], []
        for index in range(len(bins) - 1):
            mask = bin_id == index
            if mask.sum() < 3:
                continue
            centers.append(float(values[mask].mean()))
            means.append(float(observed[mask].mean()))
            errors.append(float(1.96 * observed[mask].std(ddof=1) / math.sqrt(mask.sum())))
            rows.append({"series": label, "bin": index + 1, "predicted_mean_mw": centers[-1], "observed_mean_mw": means[-1], "ci95_half_mw": errors[-1], "n": int(mask.sum())})
        style = styles[label]
        marker_face = style["color"] if label == "主模型" else "white"
        ax.errorbar(
            centers,
            means,
            yerr=errors,
            color=style["color"],
            linestyle=style["linestyle"],
            linewidth=1.2 if label == "主模型" else 0.95,
            marker=style["marker"],
            markerfacecolor=marker_face,
            markeredgecolor=style["color"],
            markeredgewidth=0.65,
            markersize=3.8,
            capsize=1.8,
            elinewidth=0.75,
            zorder=3,
        )
        _direct_label(ax, centers[-1], means[-1], label, PALETTE["ink"], dx=6, dy=-6 if label == "主模型" else 6)
    low = float(min(observed.min(), frame["baseline_mw"].min()))
    high = float(max(observed.max(), frame["predicted_mw"].max()))
    ax.plot([low, high], [low, high], color=PALETTE["ink"], linestyle=":", linewidth=float(PROFILE["reference_line_width_pt"]), alpha=0.72)
    ax.text(low + 0.13 * (high - low), low + 0.18 * (high - low), "理想校准", color=PALETTE["ink"], rotation=39, fontsize=8)
    ax.set(xlabel="分箱平均预测负荷 (MW)", ylabel="分箱平均观测负荷 (MW)", xlim=(low, high), ylim=(low, high))
    ax.set_aspect("equal", adjustable="box")
    _style_axis(ax)
    bins_path = _save_csv(pd.DataFrame(rows), folder / "calibration_bins.csv")
    slope = float(np.polyfit(frame["predicted_mw"], observed, 1)[0])
    baseline_slope = float(np.polyfit(frame["baseline_mw"], observed, 1)[0])
    return fig, {"model_calibration_slope": slope, "baseline_calibration_slope": baseline_slope, "n": len(frame)}, [path, bins_path], ["predicted_mean_mw", "observed_mean_mw", "ci95_half_mw"]


def _rmse_profile(values: np.ndarray, residual: np.ndarray, bins: int, rng: np.random.Generator) -> pd.DataFrame:
    edges = np.quantile(values, np.linspace(0, 1, bins + 1))
    index = np.clip(np.digitize(values, edges[1:-1]), 0, bins - 1)
    rows = []
    for bin_id in range(bins):
        sample = residual[index == bin_id]
        fitted = values[index == bin_id]
        boot = []
        for _ in range(300):
            draw = rng.choice(sample, size=len(sample), replace=True)
            boot.append(float(np.sqrt(np.mean(draw**2))))
        rows.append(
            {
                "bin": bin_id + 1,
                "fitted_mean_mw": float(fitted.mean()),
                "rmse_mw": float(np.sqrt(np.mean(sample**2))),
                "ci90_low_mw": float(np.quantile(boot, 0.05)),
                "ci90_high_mw": float(np.quantile(boot, 0.95)),
                "n": len(sample),
            }
        )
    return pd.DataFrame(rows)


def _residual_diagnostics(folder: Path, rng: np.random.Generator, seed: int):
    frame = _prediction_data(rng)
    observed = frame["observed_mw"].to_numpy()
    model = _rmse_profile(frame["predicted_mw"].to_numpy(), observed - frame["predicted_mw"].to_numpy(), 10, rng).assign(series="主模型")
    baseline = _rmse_profile(frame["baseline_mw"].to_numpy(), observed - frame["baseline_mw"].to_numpy(), 10, rng).assign(series="季节基线")
    profile = pd.concat([model, baseline], ignore_index=True)
    path = _save_csv(profile, folder / "residual_profile.csv")
    fig, ax = _new_figure(110)
    for subset, role in ((baseline, "baseline"), (model, "main_model")):
        style = semantic_style(role)
        x = subset["fitted_mean_mw"].to_numpy()
        y = subset["rmse_mw"].to_numpy()
        ax.fill_between(x, subset["ci90_low_mw"], subset["ci90_high_mw"], color=style["color"], alpha=0.075 if role == "baseline" else 0.10, linewidth=0)
        ax.plot(
            x,
            y,
            color=style["color"],
            linestyle=style["linestyle"],
            linewidth=1.05 if role == "baseline" else 1.45,
            marker=style["marker"],
            markerfacecolor="white" if role == "baseline" else style["color"],
            markeredgecolor=style["color"],
            markeredgewidth=0.55,
            markersize=3.4,
        )
        _direct_label(ax, x[-1], y[-1], subset["series"].iloc[0], PALETTE["ink"], dy=-7 if role == "baseline" else 7)
    ax.set(xlabel="拟合负荷分箱均值 (MW)", ylabel="残差 RMSE (MW)")
    _style_axis(ax, grid_axis="y")
    improvement = float(1 - model["rmse_mw"].mean() / baseline["rmse_mw"].mean())
    return fig, {"mean_rmse_reduction": improvement, "bins": 10, "bootstrap_repeats": 300}, [path], ["fitted_mean_mw", "rmse_mw", "ci90_low_mw", "ci90_high_mw"]


def _pareto_mask(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    keep = np.zeros(len(x), dtype=bool)
    best = np.inf
    for position in order:
        if y[position] < best:
            keep[position] = True
            best = y[position]
    return keep


def _pareto_frontier(folder: Path, rng: np.random.Generator, seed: int):
    allocations = rng.dirichlet([2.2, 1.8, 2.5, 2.0], size=900)
    cost = 68 + allocations @ np.array([10.0, 16.0, 28.0, 22.0]) + 24 * np.sum((allocations - 0.25) ** 2, axis=1)
    risk = 32 + allocations @ np.array([29.0, 18.0, 8.0, 13.0]) + 18 * np.sum((allocations - np.array([0.15, 0.23, 0.36, 0.26])) ** 2, axis=1)
    service = 0.72 + allocations @ np.array([0.10, 0.13, 0.20, 0.17]) - 0.22 * np.sum((allocations - 0.25) ** 2, axis=1)
    feasible = service >= 0.865
    local = _pareto_mask(cost[feasible], risk[feasible])
    pareto = np.zeros(len(cost), dtype=bool)
    pareto[np.where(feasible)[0][local]] = True
    frontier_indices = np.where(pareto)[0]
    nxv = (cost[frontier_indices] - cost[frontier_indices].min()) / max(np.ptp(cost[frontier_indices]), 1e-12)
    nyv = (risk[frontier_indices] - risk[frontier_indices].min()) / max(np.ptp(risk[frontier_indices]), 1e-12)
    recommended_index = frontier_indices[int(np.argmin(np.sqrt(nxv**2 + nyv**2)))]
    baseline_allocation = np.full(4, 0.25)
    baseline_cost = float(68 + baseline_allocation @ np.array([10.0, 16.0, 28.0, 22.0]))
    baseline_risk = float(32 + baseline_allocation @ np.array([29.0, 18.0, 8.0, 13.0]) + 18 * np.sum((baseline_allocation - np.array([0.15, 0.23, 0.36, 0.26])) ** 2))
    frame = pd.DataFrame({"cost_index": cost, "risk_index": risk, "service_level": service, "is_feasible": feasible, "is_pareto": pareto, "is_recommended": np.arange(len(cost)) == recommended_index})
    path = _save_csv(frame, folder / "pareto_candidates.csv")
    frontier = frame[frame["is_pareto"]].sort_values("cost_index")
    fig, ax = _new_figure(112)
    rejected = frame[~frame["is_feasible"]]
    accepted = frame[frame["is_feasible"] & ~frame["is_pareto"]]
    ax.scatter(rejected["cost_index"], rejected["risk_index"], s=4, color=PALETTE["grid"], marker="x", linewidth=0.35, alpha=0.20, zorder=1, rasterized=True)
    ax.scatter(accepted["cost_index"], accepted["risk_index"], s=5, facecolor="white", edgecolor=PALETTE["ink"], linewidth=0.28, alpha=0.16, zorder=2, rasterized=True)
    ax.plot(frontier["cost_index"], frontier["risk_index"], color=PALETTE["primary"], linewidth=1.45, zorder=4)
    ax.scatter(frontier["cost_index"], frontier["risk_index"], s=12, facecolor="white", edgecolor=PALETTE["primary"], linewidth=0.8, zorder=4)
    ax.scatter([baseline_cost], [baseline_risk], s=38, marker="s", facecolor="white", edgecolor=PALETTE["baseline"], linewidth=1.2, zorder=5)
    recommendation = frame.iloc[recommended_index]
    ax.scatter([recommendation["cost_index"]], [recommendation["risk_index"]], s=50, marker="D", color=PALETTE["highlight"], edgecolor=PALETTE["ink"], linewidth=0.55, zorder=6)
    ax.annotate("推荐解", xy=(recommendation["cost_index"], recommendation["risk_index"]), xytext=(18, 18), textcoords="offset points", arrowprops={"arrowstyle": "-", "color": PALETTE["highlight"], "lw": 0.8}, color=PALETTE["ink"], ha="left", va="bottom")
    _direct_label(ax, baseline_cost, baseline_risk, "均匀分配基线", PALETTE["ink"], dx=6, dy=8)
    frontier_label = frontier.iloc[max(len(frontier) - 4, 0)]
    _direct_label(ax, float(frontier_label["cost_index"]), float(frontier_label["risk_index"]), "Pareto 前沿", PALETTE["ink"], dx=6, dy=-8)
    ax.set(xlabel="综合成本指数（越低越好）", ylabel="运行风险指数（越低越好）")
    _style_axis(ax)
    ax.set_xlim(float(cost.min()) - 0.35, float(np.quantile(cost, 0.985)) + 0.25)
    ax.set_ylim(float(risk.min()) - 0.55, float(np.quantile(risk, 0.985)) + 0.45)
    return fig, {"candidate_count": len(frame), "feasible_count": int(feasible.sum()), "pareto_count": int(pareto.sum()), "recommended_cost": float(recommendation["cost_index"]), "recommended_risk": float(recommendation["risk_index"])}, [path], ["cost_index", "risk_index", "service_level", "is_pareto", "is_recommended"]


def _convergence(folder: Path, rng: np.random.Generator, seed: int):
    iterations = np.arange(1, 121)
    rows = []
    for run in range(16):
        main = 24 * np.exp(-iterations / rng.uniform(18, 24)) + 0.72 + rng.normal(0, 0.45, len(iterations)) * np.exp(-iterations / 55)
        baseline = 29 * np.exp(-iterations / rng.uniform(38, 48)) + 2.15 + rng.normal(0, 0.55, len(iterations)) * np.exp(-iterations / 80)
        main = np.minimum.accumulate(np.maximum(main, 0.55))
        baseline = np.minimum.accumulate(np.maximum(baseline, 1.75))
        rows.extend({"run": run + 1, "iteration": int(i), "main_gap_pct": float(m), "baseline_gap_pct": float(b)} for i, m, b in zip(iterations, main, baseline))
    frame = pd.DataFrame(rows)
    path = _save_csv(frame, folder / "convergence_runs.csv")
    fig, ax = _new_figure(108)
    endpoints = {}
    for column, role, label in (("baseline_gap_pct", "baseline", "基线算法"), ("main_gap_pct", "main_model", "改进算法")):
        group = frame.groupby("iteration")[column]
        mean = group.mean()
        low = group.quantile(0.05)
        high = group.quantile(0.95)
        style = semantic_style(role)
        ax.fill_between(iterations, low.to_numpy(), high.to_numpy(), color=style["color"], alpha=0.055 if role == "baseline" else 0.09, linewidth=0)
        ax.plot(iterations, mean.to_numpy(), color=style["color"], linestyle=style["linestyle"], linewidth=1.0 if role == "baseline" else 1.45)
        endpoints[label] = float(mean.iloc[-1])
        _direct_label(ax, iterations[-1], mean.iloc[-1], label, PALETTE["ink"], dy=7 if role == "baseline" else -7)
    threshold = 1.5
    ax.axhline(threshold, color=PALETTE["highlight"], linestyle=":", linewidth=float(PROFILE["reference_line_width_pt"]), alpha=0.9)
    ax.text(4, threshold * 1.09, "1.5% 阈值", color=PALETTE["highlight"], va="bottom", fontsize=8)
    ax.set(xlabel="迭代次数", ylabel="相对最优值差距 (%)", yscale="log")
    _style_axis(ax, grid_axis="y")
    ax.set_xlim(1, 128)
    return fig, {"runs": 16, "iterations": 120, "threshold_pct": threshold, "final_gap_pct": endpoints}, [path], ["run", "iteration", "main_gap_pct", "baseline_gap_pct"]


def _response_model(x: np.ndarray) -> np.ndarray:
    centered = 2 * x - 1
    return 70 + 8 * centered[:, 0] + 5 * centered[:, 1] ** 2 - 6 * centered[:, 2] * centered[:, 3] + 4 * np.sin(math.pi * centered[:, 4]) + 3 * centered[:, 5] ** 2 + 2.5 * centered[:, 0] * centered[:, 5]


def _sobol_estimates(rng: np.random.Generator, sample_size: int) -> tuple[np.ndarray, np.ndarray]:
    a = rng.random((sample_size, 6))
    b = rng.random((sample_size, 6))
    fa = _response_model(a)
    fb = _response_model(b)
    variance = np.var(np.concatenate([fa, fb]), ddof=1)
    first = np.empty(6)
    total = np.empty(6)
    for index in range(6):
        c = a.copy()
        c[:, index] = b[:, index]
        fc = _response_model(c)
        first[index] = np.mean(fb * (fc - fa)) / variance
        total[index] = 0.5 * np.mean((fa - fc) ** 2) / variance
    return np.clip(first, 0, 1), np.clip(total, 0, 1)


def _sensitivity(folder: Path, rng: np.random.Generator, seed: int):
    estimates = [_sobol_estimates(rng, 4096) for _ in range(14)]
    first = np.vstack([item[0] for item in estimates])
    total = np.vstack([item[1] for item in estimates])
    names = np.array(["需求弹性", "设备效率", "运输扰动", "库存系数", "周期幅度", "应急容量"])
    frame = pd.DataFrame(
        {
            "parameter": names,
            "first_order_mean": first.mean(axis=0),
            "first_order_low": np.quantile(first, 0.05, axis=0),
            "first_order_high": np.quantile(first, 0.95, axis=0),
            "total_effect_mean": total.mean(axis=0),
            "total_effect_low": np.quantile(total, 0.05, axis=0),
            "total_effect_high": np.quantile(total, 0.95, axis=0),
        }
    ).sort_values("total_effect_mean")
    path = _save_csv(frame, folder / "sobol_indices.csv")
    fig, ax = _new_figure(112)
    y = np.arange(len(frame))
    total_xerr = np.vstack([frame["total_effect_mean"] - frame["total_effect_low"], frame["total_effect_high"] - frame["total_effect_mean"]])
    first_xerr = np.vstack([frame["first_order_mean"] - frame["first_order_low"], frame["first_order_high"] - frame["first_order_mean"]])
    for yi, first_value, total_value in zip(y, frame["first_order_mean"], frame["total_effect_mean"]):
        ax.plot([first_value, total_value], [yi, yi], color=PALETTE["grid"], linewidth=2.2, solid_capstyle="round", zorder=1)
    ax.errorbar(
        frame["total_effect_mean"],
        y,
        xerr=total_xerr,
        fmt="o",
        color=PALETTE["primary"],
        markerfacecolor="white",
        markeredgewidth=1.0,
        markersize=4.8,
        capsize=2,
        elinewidth=0.85,
        linestyle="none",
        # Keep mixed Chinese/Latin labels in the normal text renderer.  A
        # MathText fragment would route the surrounding CJK glyphs through
        # Matplotlib's math font (which has no CJK coverage).
        label="总效应 (S_T)",
        zorder=3,
    )
    ax.errorbar(
        frame["first_order_mean"],
        y,
        xerr=first_xerr,
        fmt="^",
        color=PALETTE["improved"],
        markerfacecolor=PALETTE["improved"],
        markeredgecolor=PALETTE["ink"],
        markeredgewidth=0.35,
        markersize=4.2,
        capsize=1.8,
        elinewidth=0.75,
        linestyle="none",
        label="一阶效应 (S_1)",
        zorder=4,
    )
    ax.set_yticks(y, labels=frame["parameter"])
    ax.set(xlabel="Sobol 敏感性指数", ylabel="模型参数", xlim=(0, max(0.65, float(frame["total_effect_high"].max()) * 1.10)))
    _style_axis(ax, grid_axis="x")
    ax.legend(loc="lower right", ncols=1)
    interactions = float(np.maximum(frame["total_effect_mean"] - frame["first_order_mean"], 0).sum())
    return fig, {"replicates": 14, "sample_size_per_replicate": 4096, "interaction_mass": interactions}, [path], ["parameter", "first_order_mean", "total_effect_mean", "total_effect_low", "total_effect_high"]


def _robustness(folder: Path, rng: np.random.Generator, seed: int):
    scenarios = ["需求-15%", "需求+15%", "燃料+20%", "设备降效", "道路受阻", "复合冲击", "恢复阶段"]
    metrics = ["成本负担", "时延负担", "缺供风险", "碳排负担", "资源波动"]
    base = rng.normal(0, 1.8, (len(scenarios), len(metrics)))
    structured = np.array([
        [-4.2, -2.0, -3.5, -2.4, -1.0],
        [4.0, 3.2, 4.8, 2.1, 3.4],
        [6.2, 1.0, 1.5, 5.6, 2.0],
        [2.2, 5.8, 6.4, 1.6, 4.1],
        [1.4, 7.0, 5.1, 2.5, 5.7],
        [8.3, 9.2, 10.4, 6.8, 8.7],
        [-1.8, -3.0, -2.6, -1.0, -2.2],
    ])
    matrix = structured + base
    rows = [{"scenario": scenario, "metric": metric, "risk_delta_pct": float(matrix[i, j])} for i, scenario in enumerate(scenarios) for j, metric in enumerate(metrics)]
    frame = pd.DataFrame(rows)
    path = _save_csv(frame, folder / "robustness_matrix.csv")
    limit = float(np.ceil(np.max(np.abs(matrix))))
    fig, ax = _new_figure(122)
    image = ax.imshow(matrix, cmap=diverging_colormap(), vmin=-limit, vmax=limit, aspect="auto", alpha=0.84)
    ax.set_xticks(np.arange(len(metrics)), labels=metrics, rotation=18, ha="right")
    ax.set_yticks(np.arange(len(scenarios)), labels=scenarios)
    ax.set(xlabel="决策指标", ylabel="扰动情景")
    norm = Normalize(vmin=-limit, vmax=limit)
    cmap = diverging_colormap()
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = matrix[row, column]
            rgb = cmap(norm(value))[:3]
            luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
            if abs(value) >= 3.0:
                ax.text(column, row, f"{value:+.1f}", ha="center", va="center", color="white" if luminance < 0.48 else PALETTE["ink"], fontsize=7.2)
    ax.set_xticks(np.arange(-0.5, len(metrics), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(scenarios), 1), minor=True)
    ax.grid(which="minor", color=PALETTE["background"], linewidth=1.15)
    ax.tick_params(which="minor", bottom=False, left=False)
    colorbar = fig.colorbar(image, ax=ax, shrink=0.78, pad=0.02)
    colorbar.set_label("相对基线风险增量 (百分点)")
    colorbar.outline.set_edgecolor(PALETTE["grid"])
    return fig, {"scenarios": len(scenarios), "metrics": len(metrics), "maximum_risk_increase_pct": float(matrix.max())}, [path], ["scenario", "metric", "risk_delta_pct"]


def _exceedance_curve(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(values)
    probability = (len(x) - np.arange(len(x))) / (len(x) + 1)
    return x, probability


def _uncertainty(folder: Path, rng: np.random.Generator, seed: int):
    count = 8000
    common = rng.lognormal(mean=3.57, sigma=0.29, size=count)
    baseline = common + rng.gamma(3.3, 5.0, size=count)
    improved = 0.78 * common + rng.gamma(2.4, 3.2, size=count)
    threshold = 62.0
    frame = pd.DataFrame({"sample": np.arange(1, count + 1), "baseline_loss": baseline, "optimized_loss": improved})
    path = _save_csv(frame, folder / "loss_samples.csv")
    fig, ax = _new_figure(108)
    for values, role, label in ((baseline, "baseline", "基线方案"), (improved, "improved_model", "优化方案")):
        x, probability = _exceedance_curve(values)
        style = semantic_style(role)
        ax.plot(x, probability, color=style["color"], linestyle=style["linestyle"], linewidth=1.0 if role == "baseline" else 1.45)
        location = int(0.78 * len(x))
        _direct_label(ax, x[location], probability[location], label, PALETTE["ink"], dy=8 if role == "baseline" else -8)
    ax.axvline(threshold, color=PALETTE["highlight"], linestyle=":", linewidth=float(PROFILE["reference_line_width_pt"]), alpha=0.95)
    p_base = float(np.mean(baseline > threshold))
    p_improved = float(np.mean(improved > threshold))
    ax.text(threshold * 1.012, 0.68, "风险阈值", color=PALETTE["highlight"], rotation=90, va="center", fontsize=8)
    ax.text(0.02, 0.055, f"阈值超限率  {p_base:.1%} → {p_improved:.1%}", transform=ax.transAxes, color=PALETTE["ink"], va="bottom", fontsize=8)
    ax.set(xlabel="总损失指数", ylabel="超限概率  P(L > x)", yscale="log", ylim=(1e-4, 1.05))
    _style_axis(ax, grid_axis="y")
    return fig, {"samples": count, "risk_threshold": threshold, "baseline_exceedance": p_base, "optimized_exceedance": p_improved}, [path], ["baseline_loss", "optimized_loss"]


def _risk_field(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return 0.20 + 0.72 * np.exp(-((x - 5.2) ** 2 / 4.5 + (y - 3.7) ** 2 / 2.2)) + 0.28 * np.exp(-((x - 8.1) ** 2 / 1.8 + (y - 6.0) ** 2 / 1.4))


def _spatial(folder: Path, rng: np.random.Generator, seed: int):
    count = 150
    x = rng.uniform(0.3, 9.7, count)
    y = rng.uniform(0.3, 7.7, count)
    demand = rng.gamma(2.4, 18.0, count) + 8
    risk = _risk_field(x, y)
    nodes = pd.DataFrame({"node": np.arange(1, count + 1), "x_km": x, "y_km": y, "demand_units": demand, "risk_index": risk})
    nodes_path = _save_csv(nodes, folder / "spatial_nodes.csv")
    baseline_centers = np.array([[2.1, 2.0], [5.1, 3.8], [8.0, 6.0]])
    optimized_centers = np.array([[2.4, 2.3], [4.4, 6.0], [8.1, 3.0]])
    centers = pd.DataFrame(
        [{"scheme": "distance_baseline", "center": i + 1, "x_km": p[0], "y_km": p[1]} for i, p in enumerate(baseline_centers)]
        + [{"scheme": "risk_aware", "center": i + 1, "x_km": p[0], "y_km": p[1]} for i, p in enumerate(optimized_centers)]
    )
    centers_path = _save_csv(centers, folder / "service_centers.csv")
    grid_x, grid_y = np.meshgrid(np.linspace(0, 10, 160), np.linspace(0, 8, 128))
    field = _risk_field(grid_x, grid_y)
    fig, ax = _new_figure(130)
    levels = np.linspace(field.min(), field.max(), 10)
    contour = ax.contourf(grid_x, grid_y, field, levels=levels, cmap=sequential_colormap(), alpha=0.34)
    ax.contour(grid_x, grid_y, field, levels=levels[2::2], colors=PALETTE["auxiliary"], linewidths=0.45, alpha=0.45)
    sizes = 8 + 25 * (demand - demand.min()) / np.ptp(demand)
    ax.scatter(x, y, s=sizes, facecolor="white", edgecolor=PALETTE["ink"], linewidth=0.38, alpha=0.70, zorder=3)
    ax.scatter(baseline_centers[:, 0], baseline_centers[:, 1], s=46, marker="s", facecolor="white", edgecolor=PALETTE["baseline"], linewidth=1.2, zorder=5)
    ax.scatter(optimized_centers[:, 0], optimized_centers[:, 1], s=50, marker="D", color=PALETTE["highlight"], edgecolor=PALETTE["ink"], linewidth=0.5, zorder=6)
    ax.set(xlabel="东西向距离 (km)", ylabel="南北向距离 (km)", xlim=(0, 10), ylim=(0, 8), aspect="equal")
    colorbar = fig.colorbar(contour, ax=ax, shrink=0.78, pad=0.02)
    colorbar.set_label("空间风险指数")
    colorbar.outline.set_edgecolor(PALETTE["grid"])
    _direct_label(ax, baseline_centers[1, 0], baseline_centers[1, 1], "距离基线中心", PALETTE["ink"], dx=7, dy=-9, background=True)
    _direct_label(ax, optimized_centers[1, 0], optimized_centers[1, 1], "风险感知中心", PALETTE["ink"], dx=7, dy=9, background=True)
    ax.text(0.02, 0.025, "圆点大小表示需求量", transform=ax.transAxes, color=PALETTE["ink"], fontsize=8, ha="left", va="bottom")
    baseline_risk = float(_risk_field(baseline_centers[:, 0], baseline_centers[:, 1]).mean())
    optimized_risk = float(_risk_field(optimized_centers[:, 0], optimized_centers[:, 1]).mean())
    return fig, {"nodes": count, "baseline_center_risk": baseline_risk, "optimized_center_risk": optimized_risk}, [nodes_path, centers_path], ["x_km", "y_km", "demand_units", "risk_index", "scheme"]


def _network(folder: Path, rng: np.random.Generator, seed: int):
    columns, rows = 5, 4
    positions = {}
    for row in range(rows):
        for column in range(columns):
            node = row * columns + column
            positions[node] = (column * 2.4 + rng.normal(0, 0.10), row * 2.0 + rng.normal(0, 0.10))
    graph = nx.Graph()
    for node, position in positions.items():
        graph.add_node(node, pos=position, demand=float(rng.gamma(2.0, 14.0) + 5))
    for row in range(rows):
        for column in range(columns):
            node = row * columns + column
            for dc, dr in ((1, 0), (0, 1), (1, 1), (-1, 1)):
                nc, nr = column + dc, row + dr
                if 0 <= nc < columns and 0 <= nr < rows:
                    target = nr * columns + nc
                    x1, y1 = positions[node]
                    x2, y2 = positions[target]
                    distance = float(math.hypot(x2 - x1, y2 - y1))
                    midpoint_risk = float(_risk_field(np.array([(x1 + x2) / 2]), np.array([(y1 + y2) / 2]))[0])
                    graph.add_edge(node, target, distance=distance, risk=midpoint_risk, risk_weight=distance * (1 + 5.0 * midpoint_risk))
    source, target = 0, rows * columns - 1
    baseline_path = nx.shortest_path(graph, source, target, weight="distance")
    risk_path = nx.shortest_path(graph, source, target, weight="risk_weight")
    node_frame = pd.DataFrame([{"node": node, "x_km": value[0], "y_km": value[1], "demand_units": graph.nodes[node]["demand"]} for node, value in positions.items()])
    edge_frame = pd.DataFrame([{"source": left, "target": right, "distance_km": data["distance"], "risk_index": data["risk"]} for left, right, data in graph.edges(data=True)])
    route_frame = pd.DataFrame(
        [{"scheme": "distance_baseline", "order": index, "node": node} for index, node in enumerate(baseline_path)]
        + [{"scheme": "risk_aware", "order": index, "node": node} for index, node in enumerate(risk_path)]
    )
    node_path = _save_csv(node_frame, folder / "network_nodes.csv")
    edge_path = _save_csv(edge_frame, folder / "network_edges.csv")
    route_path = _save_csv(route_frame, folder / "network_routes.csv")
    fig, ax = _new_figure(122)
    nx.draw_networkx_edges(graph, positions, ax=ax, edge_color=PALETTE["grid"], width=0.55, alpha=0.55)
    demands = np.array([graph.nodes[node]["demand"] for node in graph.nodes])
    sizes = 24 + 70 * (demands - demands.min()) / np.ptp(demands)
    nx.draw_networkx_nodes(graph, positions, ax=ax, node_size=sizes, node_color="white", edgecolors=PALETTE["ink"], linewidths=0.5)

    def route_edges(route: list[int]) -> list[tuple[int, int]]:
        return list(zip(route[:-1], route[1:]))

    nx.draw_networkx_edges(graph, positions, ax=ax, edgelist=route_edges(baseline_path), edge_color=PALETTE["baseline"], width=1.45, style="dashed")
    nx.draw_networkx_edges(graph, positions, ax=ax, edgelist=route_edges(risk_path), edge_color=PALETTE["primary"], width=1.9, style="solid")
    ax.scatter(*positions[source], s=54, marker="o", color=PALETTE["improved"], edgecolor=PALETTE["ink"], linewidth=0.55, zorder=5)
    ax.scatter(*positions[target], s=58, marker="D", color=PALETTE["highlight"], edgecolor=PALETTE["ink"], linewidth=0.55, zorder=5)
    ax.set(xlabel="东西向距离 (km)", ylabel="南北向距离 (km)", aspect="equal")
    x_values = np.array([value[0] for value in positions.values()])
    y_values = np.array([value[1] for value in positions.values()])
    ax.set_xticks(np.arange(0, math.ceil(x_values.max()) + 0.1, 2.5))
    ax.set_yticks(np.arange(0, math.ceil(y_values.max()) + 0.1, 2.0))
    ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True)
    ax.grid(False)
    baseline_risk = float(sum(graph[left][right]["risk"] for left, right in route_edges(baseline_path)))
    optimized_risk = float(sum(graph[left][right]["risk"] for left, right in route_edges(risk_path)))
    baseline_mid = route_edges(baseline_path)[len(route_edges(baseline_path)) // 2]
    risk_mid = route_edges(risk_path)[len(route_edges(risk_path)) // 2]
    baseline_xy = tuple((positions[baseline_mid[0]][i] + positions[baseline_mid[1]][i]) / 2 for i in (0, 1))
    risk_xy = tuple((positions[risk_mid[0]][i] + positions[risk_mid[1]][i]) / 2 for i in (0, 1))
    _direct_label(ax, *baseline_xy, "最短距离", PALETTE["ink"], dx=6, dy=8, background=True)
    _direct_label(ax, *risk_xy, "风险感知", PALETTE["ink"], dx=6, dy=-8, background=True)
    _direct_label(ax, *positions[source], "起点", PALETTE["ink"], dx=7, dy=-8)
    _direct_label(ax, *positions[target], "终点", PALETTE["ink"], dx=-7, dy=8, ha="right")
    ax.text(0.02, 0.025, f"累计风险  {baseline_risk:.2f} → {optimized_risk:.2f}", transform=ax.transAxes, color=PALETTE["ink"], fontsize=8, ha="left", va="bottom")
    return fig, {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges(), "baseline_path": baseline_path, "risk_aware_path": risk_path, "baseline_accumulated_risk": baseline_risk, "risk_aware_accumulated_risk": optimized_risk}, [node_path, edge_path, route_path], ["source", "target", "distance_km", "risk_index", "scheme", "order"]


COMMON_RISKS = ["合成数据只用于工具验证", "不得作为竞赛主张或实证结果"]


def _enc(role: str, meaning: str, secondary: str) -> dict[str, str]:
    return {"role": role, "meaning": meaning, "secondary_encoding": secondary}


DEMO_SPECS = [
    DemoSpec("fig-01-prediction-interval", "prediction_interval", "主模型在完整测试时段内优于季节基线，且 95% 预测区间覆盖大多数观测值。", "prediction-interval", 88, [{"variable": "测试时段", "unit": "小时"}, {"variable": "系统负荷", "unit": "MW"}], "季节朴素负荷曲线", ["RMSE", "95% prediction interval", "empirical coverage", "n=120"], COMMON_RISKS, [_enc("primary", "主模型", "蓝色实线"), _enc("baseline", "季节基线", "浅蓝虚线"), _enc("ink", "观测值", "空心圆点")], _prediction_interval),
    DemoSpec("fig-02-calibration", "calibration", "主模型的分箱预测更接近理想校准线，系统性偏差小于季节基线。", "calibration", 88, [{"variable": "分箱平均预测负荷", "unit": "MW"}, {"variable": "分箱平均观测负荷", "unit": "MW"}], "季节朴素预测", ["decile binning", "95% confidence interval", "calibration slope", "n=120"], COMMON_RISKS, [_enc("primary", "主模型", "圆点实线"), _enc("baseline", "季节基线", "方点虚线"), _enc("ink", "理想校准", "点线")], _calibration),
    DemoSpec("fig-03-residual-diagnostics", "residual_diagnostics", "主模型在高负荷区间仍保持更低的残差尺度，异方差影响弱于基线。", "residual-profile", 86, [{"variable": "拟合负荷分箱均值", "unit": "MW"}, {"variable": "残差 RMSE", "unit": "MW"}], "季节朴素预测残差", ["decile residual profile", "bootstrap 90% interval", "300 bootstrap repeats"], COMMON_RISKS, [_enc("primary", "主模型残差", "圆点实线"), _enc("baseline", "基线残差", "方点虚线")], _residual_diagnostics),
    DemoSpec("fig-04-pareto-frontier", "pareto_frontier", "折中推荐解位于可行 Pareto 前沿，并同时降低均匀分配方案的成本与风险。", "pareto-frontier", 88, [{"variable": "综合成本指数", "unit": "无量纲"}, {"variable": "运行风险指数", "unit": "无量纲"}], "均匀资源分配方案", ["Pareto dominance", "service feasibility constraint", "normalized ideal-point distance", "n=900"], COMMON_RISKS, [_enc("primary", "Pareto 前沿", "蓝色实线圆点"), _enc("baseline", "均匀分配", "空心方形"), _enc("highlight", "推荐解", "橙色菱形")], _pareto_frontier),
    DemoSpec("fig-05-optimization-convergence", "optimization_convergence", "改进算法在多随机种子下更快达到收敛阈值，最终最优值差距低于基线。", "optimization-convergence", 84, [{"variable": "迭代次数", "unit": "次"}, {"variable": "相对最优值差距", "unit": "%"}], "标准启发式算法", ["16 independent seeds", "mean", "5th-95th percentile band", "monotone incumbent"], COMMON_RISKS, [_enc("primary", "改进算法", "蓝色实线"), _enc("baseline", "基线算法", "浅蓝虚线"), _enc("highlight", "收敛阈值", "橙色点线")], _convergence),
    DemoSpec("fig-06-sensitivity-ranking", "sensitivity_ranking", "需求弹性和周期幅度贡献了主要输出方差，参数交互使总效应高于一阶效应。", "global-sensitivity", 88, [{"variable": "Sobol 敏感性指数", "unit": "无量纲"}, {"variable": "模型参数", "unit": "类别"}], "名义参数组合", ["Saltelli first-order estimator", "Jansen total-effect estimator", "14 replicates", "4096 samples per replicate"], COMMON_RISKS, [_enc("primary", "总效应", "水平条形"), _enc("improved", "一阶效应", "绿色三角及误差线")], _sensitivity),
    DemoSpec("fig-07-robustness-matrix", "robustness_matrix", "复合冲击产生最大的多指标风险增量，而恢复阶段多数指标回落至基线以下。", "robustness-matrix", 94, [{"variable": "决策指标", "unit": "类别"}, {"variable": "扰动情景", "unit": "类别"}], "无扰动名义情景", ["scenario stress test", "change from matched baseline", "registered diverging colormap"], COMMON_RISKS, [_enc("primary", "风险降低", "蓝端并显示负号"), _enc("risk", "风险增加", "红端并显示正号")], _robustness),
    DemoSpec("fig-08-uncertainty-distribution", "uncertainty_distribution", "优化方案显著降低损失阈值的超限概率，并在分布尾部保持优势。", "exceedance-probability", 86, [{"variable": "总损失指数", "unit": "无量纲"}, {"variable": "超限概率", "unit": "概率"}], "未优化调度方案", ["Monte Carlo n=8000", "empirical complementary CDF", "fixed risk threshold"], COMMON_RISKS, [_enc("improved", "优化方案", "绿色实线"), _enc("baseline", "基线方案", "浅蓝虚线"), _enc("risk", "超限区域", "红色浅填充"), _enc("highlight", "风险阈值", "橙色点线")], _uncertainty),
    DemoSpec("fig-09-spatial-risk-field", "spatial_risk_field", "风险感知服务中心避开高风险核心区，同时覆盖主要需求节点。", "spatial-risk-map", 100, [{"variable": "东西向距离", "unit": "km"}, {"variable": "南北向距离", "unit": "km"}], "仅按距离布置的服务中心", ["synthetic Gaussian risk field", "demand-weighted node size", "matched center count"], COMMON_RISKS, [_enc("sequential", "风险强度", "注册连续色图"), _enc("baseline", "距离基线中心", "空心方形"), _enc("highlight", "风险感知中心", "橙色菱形")], _spatial),
    DemoSpec("fig-10-network-routes", "network_routes", "风险感知路径绕开中心高风险路段，并保持与最短距离基线相同的起终点。", "network-routing", 94, [{"variable": "东西向距离", "unit": "km"}, {"variable": "南北向距离", "unit": "km"}], "纯距离最短路径", ["Dijkstra shortest path", "risk-weighted edge cost", "node demand encoded by size"], COMMON_RISKS, [_enc("primary", "风险感知路径", "蓝色实线"), _enc("baseline", "最短距离基线", "浅蓝虚线"), _enc("size", "节点需求", "节点面积")], _network),
]


def generate_suite(output_root: Path, seed: int) -> dict:
    configure_matplotlib("publication-minimal")
    matplotlib.rcParams["svg.hashsalt"] = "python-figure-suite-v2"
    output_root.mkdir(parents=True, exist_ok=True)
    records = []
    for index, spec in enumerate(DEMO_SPECS):
        folder = output_root / spec.demo_id
        folder.mkdir(parents=True, exist_ok=True)
        rng = np.random.default_rng(np.random.SeedSequence([seed, index + 1]))
        fig, summary, source_files, fields = spec.generator(folder, rng, seed)
        records.append(_finish_demo(folder, spec, seed, fig, summary, source_files, fields))
    manifest = {
        "schema_version": 1,
        "suite_id": "python-single-figure-suite-v2",
        "style_profile": "publication-minimal",
        "synthetic_fixture": True,
        "contest_evidence_eligible": False,
        "backend": "python",
        "palette_id": "journal-spectrum-v2",
        "seed": seed,
        "python": platform.python_version(),
        "matplotlib": matplotlib.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "figure_count": len(records),
        "figures": records,
    }
    _json(output_root / "suite_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260807)
    args = parser.parse_args()
    result = generate_suite(args.output_root.resolve(), args.seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
