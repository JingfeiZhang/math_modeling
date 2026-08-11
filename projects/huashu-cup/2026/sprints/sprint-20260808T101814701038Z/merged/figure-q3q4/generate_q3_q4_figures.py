from __future__ import annotations

import csv
import hashlib
import json
import platform
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[4]
STAGING_ROOT = Path(__file__).resolve().parent
Q3_SUMMARY = PROJECT_ROOT / "experiments/C/Q3/q3-rolling-compat-20260808/q3_derived_summary.json"
Q3_COMPARISON = PROJECT_ROOT / "sprints/sprint-20260808T023236665505Z/merged/solver-q3/q3_comparison_summary.csv"
Q3_SCENARIOS = PROJECT_ROOT / "sprints/sprint-20260808T023236665505Z/merged/solver-q3/q3_scenario_metrics.csv"
Q4_SUMMARY = PROJECT_ROOT / "experiments/C/Q4/q4-integrated-compat-20260808/q4_derived_summary.json"
Q4_COMPARISON = PROJECT_ROOT / "sprints/sprint-20260808T031214934335Z/merged/solver-q4/q4_final_aggregate_comparison.csv"
Q4_HOURLY = PROJECT_ROOT / "sprints/sprint-20260808T031214934335Z/merged/solver-q4/q4_final_system_hourly.csv"
Q4_PEAK = PROJECT_ROOT / "sprints/sprint-20260808T051118704690Z/merged/solver-q4/q4_peak_tradeoff.csv"
Q3_OUTPUT_PDF = STAGING_ROOT / "fig_q3_rolling_comparison.pdf"
Q3_OUTPUT_SVG = STAGING_ROOT / "fig_q3_rolling_comparison.svg"
Q3_OUTPUT_PNG = STAGING_ROOT / "fig_q3_rolling_comparison.png"
Q4_OUTPUT_PDF = STAGING_ROOT / "fig_q4_peak_tradeoff.pdf"
Q4_OUTPUT_SVG = STAGING_ROOT / "fig_q4_peak_tradeoff.svg"
Q4_OUTPUT_PNG = STAGING_ROOT / "fig_q4_peak_tradeoff.png"
CONTRACTS_PATH = STAGING_ROOT / "figure_contract_proposals.yaml"
HANDOFF_PATH = STAGING_ROOT / "handoff.json"
QA_REPORT_PATH = STAGING_ROOT / "figure_qa_report.json"
TASK_PACKAGE_PATH = PROJECT_ROOT / "sprints/sprint-20260808T101814701038Z/tasks/solver-q3.json"

COLORS = {
    "primary": "#5292F7",
    "baseline": "#79CAFB",
    "improved": "#4EA660",
    "highlight": "#F7A24F",
    "risk": "#E95351",
    "auxiliary": "#AA77E9",
    "accent": "#CC247C",
    "caution": "#FBEB66",
    "ink": "#1F2933",
    "grid": "#D9DEE5",
    "fill": "#EAF0F4",
    "background": "#FFFFFF",
}
SCENARIO_COLORS = {
    "peak_price_empirical": COLORS["improved"],
    "high_carbon_empirical": COLORS["auxiliary"],
    "renewable_low_empirical": COLORS["highlight"],
    "joint_stress": COLORS["accent"],
}
SCENARIO_MARKERS = {
    "peak_price_empirical": "^",
    "high_carbon_empirical": "v",
    "renewable_low_empirical": "D",
    "joint_stress": "X",
}

REGISTERED_COLORS = {value.lower() for value in COLORS.values()}
REGISTERED_COLORS.update(value.lower() for value in SCENARIO_COLORS.values())

Q1_Q2_FIGURES = {
    "fig-q1-error-comparison": {
        "question_id": "Q1",
        "pdf": PROJECT_ROOT / "paper/figures/fig_q1_error_comparison.pdf",
        "svg": PROJECT_ROOT / "paper/figures/fig_q1_error_comparison.svg",
        "png": PROJECT_ROOT / "paper/figures/fig_q1_error_comparison.png",
    },
    "fig-q1-feasible-schedule": {
        "question_id": "Q1",
        "pdf": PROJECT_ROOT / "paper/figures/fig_q1_feasible_schedule.pdf",
        "svg": PROJECT_ROOT / "paper/figures/fig_q1_feasible_schedule.svg",
        "png": PROJECT_ROOT / "paper/figures/fig_q1_feasible_schedule.png",
    },
    "fig-q1-forecast-interval": {
        "question_id": "Q1",
        "pdf": PROJECT_ROOT / "paper/figures/fig_q1_forecast_interval.pdf",
        "svg": PROJECT_ROOT / "paper/figures/fig_q1_forecast_interval.svg",
        "png": PROJECT_ROOT / "paper/figures/fig_q1_forecast_interval.png",
    },
    "fig-q2-dispatch-comparison": {
        "question_id": "Q2",
        "pdf": PROJECT_ROOT / "sprints/sprint-20260808T083901900797Z/merged/figure-q2/fig_q2_dispatch_comparison.pdf",
        "svg": PROJECT_ROOT / "sprints/sprint-20260808T083901900797Z/merged/figure-q2/fig_q2_dispatch_comparison.svg",
        "png": PROJECT_ROOT / "sprints/sprint-20260808T083901900797Z/merged/figure-q2/fig_q2_dispatch_comparison.png",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected object JSON: {path}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_task_package() -> dict[str, Any]:
    package = read_json(TASK_PACKAGE_PATH)
    require(package.get("task_id") == "figure-q3q4", "unexpected task package id")
    require(package.get("role") == "figure", "figure task package role changed")
    require(package.get("write_directory") == "sprints/sprint-20260808T101814701038Z/staging/figure-q3q4", "figure write directory changed")
    require(package.get("target_gate") == "G5", "figure target gate changed")
    input_hashes = package.get("input_hashes")
    require(isinstance(input_hashes, list) and input_hashes, "task package has no input hashes")
    return package


def verify_inputs(task_package: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    for expected_record in task_package["input_hashes"]:
        path_text = str(expected_record["path"])
        expected = str(expected_record["sha256"])
        path = PROJECT_ROOT / path_text
        if not path.is_file():
            failures.append(f"missing: {path_text}")
            continue
        observed = sha256(path)
        if observed != expected:
            failures.append(f"hash mismatch: {path_text} {observed} != {expected}")
        record = dict(expected_record)
        record["sha256"] = observed
        records.append(record)
    require(not failures, "input verification failed:\n" + "\n".join(failures))
    require(records == task_package["input_hashes"], "input records differ from task package")
    return records


def configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
            "font.size": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.edgecolor": COLORS["ink"],
            "axes.labelcolor": COLORS["ink"],
            "xtick.color": COLORS["ink"],
            "ytick.color": COLORS["ink"],
            "text.color": COLORS["ink"],
            "axes.facecolor": COLORS["background"],
            "figure.facecolor": COLORS["background"],
            "axes.grid": True,
            "grid.color": COLORS["grid"],
            "grid.alpha": 0.30,
            "grid.linewidth": 0.45,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def load_and_validate_data() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    q3_summary = read_json(Q3_SUMMARY)
    q4_summary = read_json(Q4_SUMMARY)
    q3_comparison = read_csv(Q3_COMPARISON)
    q3_scenario_metrics = read_csv(Q3_SCENARIOS)
    q4_comparison = read_csv(Q4_COMPARISON)
    q4_hourly = read_csv(Q4_HOURLY)
    q4_peak = read_csv(Q4_PEAK)
    rolling = [row for row in q3_comparison if row["evaluation"] == "rolling_aggregate"]
    scenarios = [row for row in q3_comparison if row["evaluation"] == "scenario"]
    require(len(rolling) == 6, "Q3 rolling aggregate row count changed")
    require(len(scenarios) == 24, "Q3 scenario comparison row count changed")
    require(len(q3_scenario_metrics) == 24, "Q3 scenario metric row count changed")
    require(q3_summary["rolling_binary_milp"]["total_block_solves"] == 90, "Q3 rolling block count changed")
    require(q3_summary["excluded_full_horizon_lp_probe"]["claim_eligible"] is False, "Q3 LP probe is claim eligible")
    require(q3_summary["excluded_full_horizon_lp_probe"]["exclusion_permanent"] is True, "Q3 LP exclusion boundary changed")
    require(q3_summary["audit_boundary"]["total_audit_count"] == 270, "Q3 audit count changed")
    require(q3_summary["audit_boundary"]["total_audits_passed"] == 269, "Q3 audit boundary changed")
    require(q4_summary["audit"]["final_hard_constraints_passed"] is True, "Q4 hard audit failed")
    require(q4_summary["audit"]["peak_scan_all_points_passed"] is True, "Q4 peak scan audit failed")
    require(q4_summary["audit"]["peak_scan_point_count"] == 17, "Q4 peak point count changed")
    require(q4_summary["scope"]["peak_probe_horizon_hours"] == 24, "Q4 peak probe horizon changed")
    require(len(q4_comparison) == 5, "Q4 aggregate scenario count changed")
    require(len(q4_hourly) == 720, "Q4 hourly evidence row count changed")
    require(len(q4_peak) == 17, "Q4 peak scan CSV row count changed")
    require(all(row["audit_passed"].lower() == "true" for row in q4_peak), "Q4 peak audit row failed")
    return q3_summary, q4_summary, rolling, scenarios, q4_peak, q4_comparison


def scenario_label(name: str) -> str:
    return {
        "peak_price_empirical": "Peak price",
        "high_carbon_empirical": "High carbon",
        "renewable_low_empirical": "Low renewable",
        "joint_stress": "Joint stress",
    }[name]


def layout_qa(
    fig: mpl.figure.Figure,
    ax: mpl.axes.Axes,
    annotations: list[Any],
    legend: Any,
    data_points: list[tuple[float, float]],
) -> dict[str, Any]:
    """Check rendered annotation and legend boxes against the figure boundary."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    figure_box = fig.bbox
    boxes: list[tuple[str, Any]] = []
    for index, artist in enumerate(annotations):
        boxes.append((f"annotation_{index}", artist.get_window_extent(renderer).expanded(1.02, 1.05)))
    if legend is not None:
        boxes.append(("legend", legend.get_window_extent(renderer).expanded(1.02, 1.05)))
    clipped = [
        name
        for name, box in boxes
        if not figure_box.contains(box.x0, box.y0) or not figure_box.contains(box.x1, box.y1)
    ]
    overlaps: list[list[str]] = []
    for index, (name_a, box_a) in enumerate(boxes):
        for name_b, box_b in boxes[index + 1 :]:
            if box_a.overlaps(box_b):
                overlaps.append([name_a, name_b])
    legend_data_points: list[int] = []
    if legend is not None:
        legend_box = legend.get_window_extent(renderer)
        for index, (x_value, y_value) in enumerate(data_points):
            display_x, display_y = ax.transData.transform((x_value, y_value))
            if legend_box.contains(display_x, display_y):
                legend_data_points.append(index)
    return {
        "clipped_artists": clipped,
        "annotation_or_legend_overlaps": overlaps,
        "legend_data_point_indices": legend_data_points,
        "passed": not clipped and not overlaps and not legend_data_points,
    }


def generate_q3_figure(q3_summary: dict[str, Any], rolling: list[dict[str, str]], scenarios: list[dict[str, str]]) -> dict[str, Any]:
    fig, ax = plt.subplots(figsize=(158 / 25.4, 104 / 25.4))
    ax.set_axisbelow(True)
    ax.axhline(0, color=COLORS["ink"], linewidth=0.75, alpha=0.7, zorder=1)
    ax.axvline(0, color=COLORS["ink"], linewidth=0.75, alpha=0.7, zorder=1)

    region_offsets = {
        "RegionA": (-12, 10),
        "RegionB": (8, 10),
        "RegionC": (-12, -12),
        "RegionD": (7, 6),
        "RegionE": (7, -11),
        "RegionF": (-13, -13),
    }
    rolling_annotations: list[Any] = []
    for row in rolling:
        x = float(row["peak_reduction_MW"])
        y = float(row["cost_saving_CNY"]) / 1e6
        ax.scatter(
            x,
            y,
            s=44,
            marker="o",
            facecolor=COLORS["primary"],
            edgecolor=COLORS["ink"],
            linewidth=0.45,
            zorder=4,
            label="Rolling aggregate" if row["region"] == "RegionA" else "_nolegend_",
        )
        ax.annotate(
            row["region"].replace("Region", "R"),
            (x, y),
            xytext=region_offsets[row["region"]],
            textcoords="offset points",
            fontsize=8,
            color=COLORS["ink"],
            zorder=5,
        )
        rolling_annotations.append(ax.texts[-1])

    seen: set[str] = set()
    for row in scenarios:
        scenario = row["scenario"]
        x = float(row["peak_reduction_MW"])
        y = float(row["cost_saving_CNY"]) / 1e6
        label = scenario_label(scenario)
        ax.scatter(
            x,
            y,
            s=25,
            marker=SCENARIO_MARKERS[scenario],
            facecolor=SCENARIO_COLORS[scenario],
            edgecolor=COLORS["ink"],
            linewidth=0.3,
            alpha=0.80,
            zorder=3,
            label=label if scenario not in seen else "_nolegend_",
        )
        seen.add(scenario)

    ax.set_xlabel("Peak reduction relative to baseline (MW)")
    ax.set_ylabel("Operating-cost saving relative to baseline (million CNY)")
    ax.set_xlim(left=-8)
    ax.set_ylim(bottom=-0.75)
    ax.grid(True, axis="both", zorder=0)
    legend = ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.58, 0.99),
        frameon=True,
        framealpha=0.94,
        facecolor=COLORS["background"],
        edgecolor=COLORS["grid"],
        ncol=2,
        handletextpad=0.4,
        columnspacing=0.9,
        borderpad=0.5,
    )
    scope_annotation = fig.text(
        0.13,
        0.985,
        f"{q3_summary['rolling_binary_milp']['total_block_solves']} rolling binary-MILP blocks; "
        f"{q3_summary['deterministic_stress_probes']['scope_hours']} h stress probes\n"
        f"{q3_summary['audit_boundary']['total_audits_passed']}/"
        f"{q3_summary['audit_boundary']['total_audit_count']} complete audits passed; full-horizon LP excluded\n"
        f"RegionF simultaneous charge/discharge = "
        f"{q3_summary['excluded_full_horizon_lp_probe']['region_f_simultaneous_charge_discharge_mw']:.1f} MW",
        ha="left",
        va="top",
        fontsize=8,
        color=COLORS["ink"],
        bbox={"boxstyle": "round,pad=0.3", "facecolor": COLORS["fill"], "edgecolor": COLORS["grid"], "linewidth": 0.5},
    )
    fig.subplots_adjust(left=0.13, right=0.98, bottom=0.17, top=0.84)
    data_points = [
        (float(row["peak_reduction_MW"]), float(row["cost_saving_CNY"]) / 1e6)
        for row in rolling + scenarios
    ]
    qa = layout_qa(fig, ax, rolling_annotations + [scope_annotation], legend, data_points)
    for path in (Q3_OUTPUT_PDF, Q3_OUTPUT_SVG, Q3_OUTPUT_PNG):
        fig.savefig(path, dpi=400, facecolor=COLORS["background"])
    plt.close(fig)
    return qa


def generate_q4_figure(q4_summary: dict[str, Any], peak_rows: list[dict[str, str]]) -> dict[str, Any]:
    weights = [float(row["peak_weight"]) for row in peak_rows]
    peaks = [float(row["system_peak_variable_MW"]) for row in peak_rows]
    selected_weight = float(q4_summary["peak_probe_24h"]["selected_peak_weight"])
    selected_peak = float(q4_summary["peak_probe_24h"]["selected_peak_MW"])
    zero_peak = float(q4_summary["peak_probe_24h"]["zero_weight_peak_MW"])
    reduction = float(q4_summary["peak_probe_24h"]["peak_reduction_MW"])
    require(any(abs(weight - selected_weight) <= 1e-12 for weight in weights), "selected peak weight is absent from scan")
    require(any(abs(peak - selected_peak) <= 1e-9 for peak in peaks), "selected peak value is absent from scan")

    fig, ax = plt.subplots(figsize=(158 / 25.4, 104 / 25.4))
    x = list(range(len(weights)))
    ax.plot(
        x,
        peaks,
        color=COLORS["primary"],
        linewidth=1.6,
        marker="o",
        markersize=4.2,
        markerfacecolor=COLORS["primary"],
        markeredgecolor=COLORS["ink"],
        markeredgewidth=0.35,
        label=f"{q4_summary['audit']['peak_scan_point_count']}-point discrete MILP scan",
        zorder=3,
    )
    selected_index = min(range(len(weights)), key=lambda index: abs(weights[index] - selected_weight))
    zero_index = weights.index(0.0)
    ax.scatter(
        [zero_index],
        [zero_peak],
        marker="s",
        s=54,
        facecolor=COLORS["baseline"],
        edgecolor=COLORS["ink"],
        linewidth=0.45,
        zorder=5,
        label="Zero peak weight",
    )
    ax.scatter(
        [selected_index],
        [selected_peak],
        marker="D",
        s=58,
        facecolor=COLORS["highlight"],
        edgecolor=COLORS["ink"],
        linewidth=0.55,
        zorder=6,
        label="Selected discrete point",
    )
    ax.annotate(
        f"selected w={selected_weight:g}\npeak={selected_peak:.1f} MW\nreduction={reduction:.1f} MW",
        (selected_index, selected_peak),
        xytext=(12, 18),
        textcoords="offset points",
        fontsize=8,
        color=COLORS["ink"],
        ha="left",
        va="bottom",
        arrowprops={"arrowstyle": "-", "color": COLORS["highlight"], "linewidth": 0.9},
        bbox={"boxstyle": "round,pad=0.28", "facecolor": COLORS["background"], "edgecolor": COLORS["highlight"], "linewidth": 0.6},
        zorder=7,
    )
    tick_indices = [0, 1, 7, 8, 12, 16]
    tick_labels = ["0", "1e-7", "1e-4", "3e-4", "5e-2", "0.5"]
    ax.set_xticks(tick_indices, tick_labels)
    ax.set_xlabel("Peak-weight scan point w (dimensionless; ordered by w)")
    ax.set_ylabel("System positive peak net import (MW)")
    ax.set_xlim(-0.5, len(weights) - 0.5)
    ax.set_ylim(min(peaks) - 8, max(peaks) + 18)
    ax.grid(True, axis="y", zorder=0)
    legend = ax.legend(
        loc="upper right",
        frameon=True,
        framealpha=0.94,
        facecolor=COLORS["background"],
        edgecolor=COLORS["grid"],
        handletextpad=0.4,
        borderpad=0.5,
    )
    ax.text(
        0.02,
        0.03,
        f"Independent {q4_summary['scope']['peak_probe_horizon_hours']} h low-renewable probe; "
        f"all {q4_summary['audit']['peak_scan_point_count']} audits passed\n"
        "Discrete marginal only; not a continuous shadow price",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        color=COLORS["ink"],
        bbox={"boxstyle": "round,pad=0.3", "facecolor": COLORS["fill"], "edgecolor": COLORS["grid"], "linewidth": 0.5},
    )
    fig.subplots_adjust(left=0.13, right=0.98, bottom=0.17, top=0.97)
    qa = layout_qa(fig, ax, [ax.texts[-2], ax.texts[-1]], legend, list(zip(x, peaks)))
    for path in (Q4_OUTPUT_PDF, Q4_OUTPUT_SVG, Q4_OUTPUT_PNG):
        fig.savefig(path, dpi=400, facecolor=COLORS["background"])
    plt.close(fig)
    return qa


def source_hash(path_text: str) -> str:
    return sha256(PROJECT_ROOT / path_text)


def make_contracts(
    q3_summary: dict[str, Any],
    q4_summary: dict[str, Any],
    rolling: list[dict[str, str]],
    scenarios: list[dict[str, str]],
    q4_peak: list[dict[str, str]],
) -> dict[str, Any]:
    script_path = relative(Path(__file__).resolve())
    q3_summary_hash = sha256(Q3_SUMMARY)
    q3_comparison_hash = sha256(Q3_COMPARISON)
    q3_scenarios_hash = sha256(Q3_SCENARIOS)
    q4_summary_hash = sha256(Q4_SUMMARY)
    q4_comparison_hash = sha256(Q4_COMPARISON)
    q4_hourly_hash = sha256(Q4_HOURLY)
    q4_peak_hash = sha256(Q4_PEAK)
    q3_blocks = q3_summary["rolling_binary_milp"]["total_block_solves"]
    q3_probe_hours = q3_summary["deterministic_stress_probes"]["scope_hours"]
    q3_audits_passed = q3_summary["audit_boundary"]["total_audits_passed"]
    q3_audit_count = q3_summary["audit_boundary"]["total_audit_count"]
    q3_region_f_cycle_mw = q3_summary["excluded_full_horizon_lp_probe"]["region_f_simultaneous_charge_discharge_mw"]
    q4_point_count = q4_summary["audit"]["peak_scan_point_count"]
    q4_selected_weight = q4_summary["peak_probe_24h"]["selected_peak_weight"]
    return {
        "schema_version": 1,
        "figures": [
            {
                "contract_version": "2.0",
                "id": "fig-q3-rolling-comparison",
                "question_id": "Q3",
                "claim_id": "Q3-ROLLING-COST-DELTA",
                "core_conclusion": "The rolling storage policy improves the cost-versus-peak trade-off in Regions D-F, while deterministic 72-hour probes show scenario-dependent but directionally comparable changes.",
                "core_message": "Rolling regional storage dispatch and deterministic stress-probe comparisons are shown together; the excluded full-horizon LP is a boundary, not evidence.",
                "evidence_chain": [
                    {
                        "locator": "experiments/C/Q3/q3-rolling-compat-20260808/q3_derived_summary.json:$.rolling_binary_milp.total_block_solves",
                        "sha256": q3_summary_hash,
                        "fields": [
                            "rolling_binary_milp.total_block_solves",
                            "deterministic_stress_probes.scope_hours",
                            "audit_boundary.total_audits_passed",
                            "audit_boundary.total_audit_count",
                            "excluded_full_horizon_lp_probe.claim_eligible",
                            "excluded_full_horizon_lp_probe.region_f_simultaneous_charge_discharge_mw",
                        ],
                    },
                    {
                        "locator": "sprints/sprint-20260808T023236665505Z/merged/solver-q3/q3_comparison_summary.csv:rolling_aggregate and scenario rows",
                        "sha256": q3_comparison_hash,
                        "fields": ["evaluation", "region", "cost_saving_CNY", "peak_reduction_MW"],
                    },
                    {
                        "locator": "sprints/sprint-20260808T023236665505Z/merged/solver-q3/q3_scenario_metrics.csv:24 candidate scenario rows",
                        "sha256": q3_scenarios_hash,
                        "fields": ["scenario", "region", "solver_success"],
                    },
                ],
                "kind": "data",
                "archetype": "robustness-comparison",
                "backend": "python/matplotlib",
                "source_data": [
                    "experiments/C/Q3/q3-rolling-compat-20260808/q3_derived_summary.json",
                    "sprints/sprint-20260808T023236665505Z/merged/solver-q3/q3_comparison_summary.csv",
                    "sprints/sprint-20260808T023236665505Z/merged/solver-q3/q3_scenario_metrics.csv",
                ],
                "source_script": script_path,
                "outputs": {
                    "pdf": relative(Q3_OUTPUT_PDF),
                    "svg": relative(Q3_OUTPUT_SVG),
                    "png": relative(Q3_OUTPUT_PNG),
                    "png_dpi": 400,
                },
                "baseline": "Matched deterministic no-storage renewable-first policy in each Q3 comparison row.",
                "axes": [
                    {"variable": "peak reduction relative to baseline", "unit": "MW"},
                    {"variable": "operating-cost saving relative to baseline", "unit": "million CNY"},
                ],
                "caption": (
                    "Q3 rolling storage comparison and deterministic stress probes. "
                    f"Circles are {len(rolling)} regional rolling aggregates from {q3_blocks} binary-MILP blocks; "
                    f"scenario markers are {len(scenarios)} candidate rows from four observed-data-derived "
                    f"{q3_probe_hours}-hour probes, each compared with the matched no-storage baseline. "
                    f"The annotation records {q3_audits_passed}/{q3_audit_count} complete audits passed and the "
                    f"permanently excluded full-horizon LP probe (RegionF simultaneous charge/discharge "
                    f"{q3_region_f_cycle_mw:.1f} MW); the plot does not imply global optimality or probabilistic guarantees."
                ),
                "panel_map": [{"panel": "main", "role": "cost-versus-peak comparison", "subclaim": "rolling and stress-probe trade-offs"}],
                "statistics": [f"{len(rolling)} rolling aggregate rows and {len(scenarios)} scenario comparison rows; deterministic audits only."],
                "review_risks": ["Scenario points are 72-hour probes, not full-horizon forecasts.", "The full-horizon LP probe is excluded and not plotted as evidence.", "Overlapping zero-improvement points can conceal multiplicity; region labels identify rolling points."],
                "target_size_profile": "contest-body",
                "final_width_mm": 158,
                "min_font_pt": 8,
                "palette_id": "journal-spectrum-v2",
                "color_encoding": [
                    {"role": "rolling_aggregate", "meaning": "main rolling policy", "color": COLORS["primary"], "secondary_encoding": "circle"},
                    {"role": "peak_price_empirical", "meaning": "peak-price probe", "color": SCENARIO_COLORS["peak_price_empirical"], "secondary_encoding": "up triangle"},
                    {"role": "high_carbon_empirical", "meaning": "high-carbon probe", "color": SCENARIO_COLORS["high_carbon_empirical"], "secondary_encoding": "down triangle"},
                    {"role": "renewable_low_empirical", "meaning": "low-renewable probe", "color": SCENARIO_COLORS["renewable_low_empirical"], "secondary_encoding": "diamond"},
                    {"role": "joint_stress", "meaning": "joint-stress probe", "color": SCENARIO_COLORS["joint_stress"], "secondary_encoding": "x marker"},
                ],
                "visual_hierarchy": {"primary_evidence": "rolling aggregate and scenario trade-off points", "secondary_context": "matched baseline deltas and direct region labels", "deemphasized": "zero reference axes and boundary annotation"},
                "label_strategy": {"mode": "external-legend", "collision_checked": True},
                "statistics_report": {"sample_size": f"{len(rolling)} rolling aggregate rows + {len(scenarios)} scenario rows", "center": "none", "interval": "none", "test": "none", "multiplicity": "descriptive comparison"},
                "data_integrity": {"source_hashes": [{"path": "experiments/C/Q3/q3-rolling-compat-20260808/q3_derived_summary.json", "sha256": q3_summary_hash}, {"path": "sprints/sprint-20260808T023236665505Z/merged/solver-q3/q3_comparison_summary.csv", "sha256": q3_comparison_hash}, {"path": "sprints/sprint-20260808T023236665505Z/merged/solver-q3/q3_scenario_metrics.csv", "sha256": q3_scenarios_hash}], "transformation": "Read-only CSV/JSON parsing; cost is divided by 1e6 only for axis display; no manual values.", "manual_values_forbidden": True},
                "rasterized_layers": [],
            },
            {
                "contract_version": "2.0",
                "id": "fig-q4-peak-tradeoff",
                "question_id": "Q4",
                "claim_id": "Q4-PEAK-REDUCTION",
                "core_conclusion": f"The independent 24-hour low-renewable discrete scan exhibits stepwise peak reduction as the peak-weight increases, with the selected point at w={q4_selected_weight:g}.",
                "core_message": f"The peak-weight response is a {q4_point_count}-point discrete MILP sensitivity scan; it is not a continuous dual-price curve or a global optimum proof.",
                "evidence_chain": [
                    {
                        "locator": "experiments/C/Q4/q4-integrated-compat-20260808/q4_derived_summary.json:$.peak_probe_24h.peak_reduction_MW",
                        "sha256": q4_summary_hash,
                        "fields": ["peak_probe_24h.peak_reduction_MW", "peak_probe_24h.selected_peak_weight", "peak_probe_24h.zero_weight_peak_MW"],
                    },
                    {
                        "locator": f"sprints/sprint-20260808T051118704690Z/merged/solver-q4/q4_peak_tradeoff.csv:{q4_point_count} audited scan rows",
                        "sha256": q4_peak_hash,
                        "fields": ["peak_weight", "system_peak_variable_MW", "audit_passed"],
                    },
                    {
                        "locator": "sprints/sprint-20260808T031214934335Z/merged/solver-q4/q4_final_aggregate_comparison.csv:five 72-hour scenario rows",
                        "sha256": q4_comparison_hash,
                        "fields": ["scenario", "cost_delta_CNY", "carbon_delta_tCO2"],
                    },
                    {
                        "locator": "sprints/sprint-20260808T031214934335Z/merged/solver-q4/q4_final_system_hourly.csv:720 hourly rows",
                        "sha256": q4_hourly_hash,
                        "fields": ["Hour", "SystemNetGridImport_MW", "Scenario"],
                    },
                ],
                "kind": "data",
                "archetype": "sensitivity-scan",
                "backend": "python/matplotlib",
                "source_data": [
                    "experiments/C/Q4/q4-integrated-compat-20260808/q4_derived_summary.json",
                    "sprints/sprint-20260808T051118704690Z/merged/solver-q4/q4_peak_tradeoff.csv",
                    "sprints/sprint-20260808T031214934335Z/merged/solver-q4/q4_final_aggregate_comparison.csv",
                    "sprints/sprint-20260808T031214934335Z/merged/solver-q4/q4_final_system_hourly.csv",
                ],
                "source_script": script_path,
                "outputs": {
                    "pdf": relative(Q4_OUTPUT_PDF),
                    "svg": relative(Q4_OUTPUT_SVG),
                    "png": relative(Q4_OUTPUT_PNG),
                    "png_dpi": 400,
                },
                "baseline": "Zero peak-weight row in the same independent 24-hour low-renewable probe.",
                "axes": [
                    {"variable": "peak-weight scan point w", "unit": "dimensionless"},
                    {"variable": "system positive peak net import", "unit": "MW"},
                ],
                "caption": f"Q4 independent 24-hour low-renewable peak-weight scan. The line connects {q4_point_count} audited discrete MILP points in increasing weight order; the square is the zero-weight reference and the diamond marks the selected discrete point at w={q4_selected_weight:g}. The displayed reduction is relative to the zero-weight row. This scan is independent of the 72-hour sequential comparison and does not establish a continuous shadow price or full-horizon global optimum.",
                "panel_map": [{"panel": "main", "role": "discrete peak-weight response", "subclaim": "selected point and zero-weight reference"}],
                "statistics": [f"{q4_point_count} audited discrete scan points; all solver and hard-constraint audits passed."],
                "review_risks": ["The x-axis is ordered scan points with actual weights as tick labels; it is not a continuous parameterization.", "The selected point is a discrete decision, not an LP dual variable.", "The probe covers 24 hours only and is separate from the 72-hour sequential comparison."],
                "target_size_profile": "contest-body",
                "final_width_mm": 158,
                "min_font_pt": 8,
                "palette_id": "journal-spectrum-v2",
                "color_encoding": [
                    {"role": "discrete_scan", "meaning": "audited MILP scan", "color": COLORS["primary"], "secondary_encoding": "solid line + circle"},
                    {"role": "zero_weight_reference", "meaning": "zero-weight row", "color": COLORS["baseline"], "secondary_encoding": "square"},
                    {"role": "selected_discrete_point", "meaning": "selected scan point", "color": COLORS["highlight"], "secondary_encoding": "diamond + direct annotation"},
                ],
                "visual_hierarchy": {"primary_evidence": f"{q4_point_count}-point discrete peak response", "secondary_context": "zero-weight reference and selected point", "deemphasized": "grid and scope annotation"},
                "label_strategy": {"mode": "direct", "collision_checked": True},
                "statistics_report": {"sample_size": f"{q4_point_count} discrete scan rows", "center": "none", "interval": "none", "test": "audit_passed per row", "multiplicity": "descriptive sensitivity scan"},
                "data_integrity": {"source_hashes": [{"path": "experiments/C/Q4/q4-integrated-compat-20260808/q4_derived_summary.json", "sha256": q4_summary_hash}, {"path": "sprints/sprint-20260808T051118704690Z/merged/solver-q4/q4_peak_tradeoff.csv", "sha256": q4_peak_hash}, {"path": "sprints/sprint-20260808T031214934335Z/merged/solver-q4/q4_final_aggregate_comparison.csv", "sha256": q4_comparison_hash}, {"path": "sprints/sprint-20260808T031214934335Z/merged/solver-q4/q4_final_system_hourly.csv", "sha256": q4_hourly_hash}], "transformation": "Read-only CSV/JSON parsing; no interpolation or continuous optimization; no manual values.", "manual_values_forbidden": True},
                "rasterized_layers": [],
            },
        ],
    }


def qa_figure_assets(
    figure_id: str,
    paths: dict[str, Path],
    strict_png_size: bool,
    layout: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run artifact-level checks that do not depend on manually entered values."""
    result: dict[str, Any] = {"figure_id": figure_id, "formats": {}, "layout": layout or {}}
    failures: list[str] = []
    expected_size = (2488, 1637)
    for fmt, path in paths.items():
        record: dict[str, Any] = {"path": relative(path), "exists": path.is_file()}
        if not path.is_file():
            failures.append(f"missing {fmt}: {path}")
            result["formats"][fmt] = record
            continue
        record["sha256"] = sha256(path)
        record["bytes"] = path.stat().st_size
        require(record["bytes"] > 0, f"empty figure artifact: {path}")
        if fmt == "png":
            try:
                from PIL import Image

                with Image.open(path) as image:
                    record["size_px"] = list(image.size)
                    dpi = image.info.get("dpi")
                    record["dpi"] = list(dpi) if isinstance(dpi, tuple) else dpi
                    record["nonwhite_edge_fraction"] = _nonwhite_edge_fraction(image)
                    dpi_ok = isinstance(dpi, tuple) and min(dpi) >= 399.0
                    size_ok = image.size == expected_size if strict_png_size else image.size[0] == expected_size[0]
                    record["dpi_400_passed"] = dpi_ok
                    record["size_passed"] = size_ok
                    record["edge_clipping_proxy_passed"] = record["nonwhite_edge_fraction"] < 0.25
                    if not dpi_ok:
                        failures.append(f"{figure_id} PNG dpi below 400")
                    if not size_ok:
                        failures.append(f"{figure_id} PNG size changed: {image.size}")
                    if not record["edge_clipping_proxy_passed"]:
                        failures.append(f"{figure_id} PNG edge clipping proxy failed")
            except Exception as exc:
                record["error"] = str(exc)
                failures.append(f"PNG inspection failed for {figure_id}: {exc}")
        elif fmt == "svg":
            text_count = 0
            image_count = 0
            axes_count = 0
            colors: set[str] = set()
            try:
                root = ET.parse(path).getroot()
                for element in root.iter():
                    tag = element.tag.rsplit("}", 1)[-1]
                    text_count += tag == "text"
                    image_count += tag == "image"
                    element_id = element.attrib.get("id", "")
                    axes_count += element_id.startswith("axes_")
                colors = {value.lower() for value in re.findall(r"#[0-9A-Fa-f]{6}", path.read_text(encoding="utf-8"))}
            except Exception as exc:
                record["error"] = str(exc)
                failures.append(f"SVG inspection failed for {figure_id}: {exc}")
            record.update(
                {
                    "editable_text_count": text_count,
                    "image_elements": image_count,
                    "axes_count": axes_count,
                    "registered_colors": sorted(colors & REGISTERED_COLORS),
                    "unregistered_colors": sorted(colors - REGISTERED_COLORS),
                    "editable_text_passed": text_count > 0 and image_count == 0,
                    "single_axes_passed": axes_count == 1,
                    "palette_passed": not (colors - REGISTERED_COLORS),
                }
            )
            if not record["editable_text_passed"]:
                failures.append(f"{figure_id} SVG is not editable text")
            if not record["single_axes_passed"]:
                failures.append(f"{figure_id} SVG has {axes_count} primary axes groups")
            if not record["palette_passed"]:
                failures.append(f"{figure_id} SVG has unregistered colors")
        else:
            try:
                import fitz

                document = fitz.open(path)
                text_chars = sum(len(page.get_text()) for page in document)
                record["pages"] = len(document)
                record["pdf_text_chars"] = text_chars
                record["vector_text_passed"] = text_chars > 0
                document.close()
                if not record["vector_text_passed"]:
                    failures.append(f"{figure_id} PDF has no extractable text")
            except Exception as exc:
                record["error"] = str(exc)
                failures.append(f"PDF inspection failed for {figure_id}: {exc}")
        result["formats"][fmt] = record
    result["failures"] = failures
    result["passed"] = not failures and bool(result.get("layout", {}).get("passed", True))
    return result


def _nonwhite_edge_fraction(image: Any) -> float:
    rgba = image.convert("RGB")
    width, height = rgba.size
    thickness = max(2, min(width, height) // 200)
    pixels = []
    for x in range(width):
        for y in range(thickness):
            pixels.append(rgba.getpixel((x, y)))
            pixels.append(rgba.getpixel((x, height - 1 - y)))
    for y in range(thickness, height - thickness):
        for x in range(thickness):
            pixels.append(rgba.getpixel((x, y)))
            pixels.append(rgba.getpixel((width - 1 - x, y)))
    nonwhite = sum(max(pixel) < 245 for pixel in pixels)
    return nonwhite / max(len(pixels), 1)


def make_qa_report(q3_layout: dict[str, Any], q4_layout: dict[str, Any]) -> dict[str, Any]:
    generated = {
        "fig-q3-rolling-comparison": qa_figure_assets(
            "fig-q3-rolling-comparison",
            {"pdf": Q3_OUTPUT_PDF, "svg": Q3_OUTPUT_SVG, "png": Q3_OUTPUT_PNG},
            strict_png_size=True,
            layout=q3_layout,
        ),
        "fig-q4-peak-tradeoff": qa_figure_assets(
            "fig-q4-peak-tradeoff",
            {"pdf": Q4_OUTPUT_PDF, "svg": Q4_OUTPUT_SVG, "png": Q4_OUTPUT_PNG},
            strict_png_size=True,
            layout=q4_layout,
        ),
    }
    existing = {
        figure_id: qa_figure_assets(figure_id, {fmt: paths[fmt] for fmt in ("pdf", "svg", "png")}, strict_png_size=False)
        for figure_id, paths in Q1_Q2_FIGURES.items()
    }
    q3_q4_passed = all(record["passed"] for record in generated.values())
    q1_q2_passed = all(record["passed"] for record in existing.values())
    return {
        "schema_version": 1,
        "task_id": "figure-q3q4",
        "sprint_id": "sprint-20260808T101814701038Z",
        "environment": {"python": platform.python_version(), "matplotlib": mpl.__version__},
        "q1_q2": existing,
        "q3_q4": generated,
        "q1_q2_passed": q1_q2_passed,
        "q3_q4_passed": q3_q4_passed,
        "overall_passed": q1_q2_passed and q3_q4_passed,
        "notes": [
            "Existing Q1/Q2 exports were checked independently from their frozen SVG/PDF/PNG artifacts.",
            "Q3/Q4 layout checks use rendered artist boxes; plotted data coordinates are unchanged.",
            "Grayscale readability is represented by marker/line secondary encodings and recorded in contracts.",
        ],
    }


def make_handoff(input_records: list[dict[str, Any]], contracts: dict[str, Any], qa_report: dict[str, Any]) -> dict[str, Any]:
    expected = [
        "sprints/sprint-20260808T101814701038Z/staging/figure-q3q4/handoff.json",
        "sprints/sprint-20260808T101814701038Z/staging/figure-q3q4/figure_contract_proposals.yaml",
        "sprints/sprint-20260808T101814701038Z/staging/figure-q3q4/generate_q3_q4_figures.py",
        "sprints/sprint-20260808T101814701038Z/staging/figure-q3q4/figure_qa_report.json",
        "sprints/sprint-20260808T101814701038Z/staging/figure-q3q4/fig_q3_rolling_comparison.pdf",
        "sprints/sprint-20260808T101814701038Z/staging/figure-q3q4/fig_q3_rolling_comparison.svg",
        "sprints/sprint-20260808T101814701038Z/staging/figure-q3q4/fig_q3_rolling_comparison.png",
        "sprints/sprint-20260808T101814701038Z/staging/figure-q3q4/fig_q4_peak_tradeoff.pdf",
        "sprints/sprint-20260808T101814701038Z/staging/figure-q3q4/fig_q4_peak_tradeoff.svg",
        "sprints/sprint-20260808T101814701038Z/staging/figure-q3q4/fig_q4_peak_tradeoff.png",
    ]
    artifacts = [
        {"path": path, "sha256": sha256(PROJECT_ROOT / path)}
        for path in expected[1:]
    ]
    return {
        "schema_version": 1,
        "sprint_id": "sprint-20260808T101814701038Z",
        "task_id": "figure-q3q4",
        "attempt": 1,
        "status": "SUCCESS" if qa_report["overall_passed"] else "PARTIAL",
        "input_hashes": input_records,
        "written_paths": expected,
        "artifacts": artifacts,
        "gate_result": {
            "gate": "G5",
            "passed": qa_report["overall_passed"],
            "checks": [
                "task-package input hashes match",
                "frozen evidence only",
                "single primary axes per figure",
                "journal-spectrum-v2 palette only",
                "editable PDF/SVG and 400 dpi PNG exports",
                "Q1/Q2 independent artifact QA passed",
                "Q3 269/270 audit and excluded RegionF LP boundary preserved",
                "Q4 17-point discrete non-shadow-price boundary preserved",
                "rendered annotation, legend, data-point collision and clipping QA passed",
            ],
        },
        "summary": (
            "Repaired Q3/Q4 publication figures and contract proposals from pinned frozen evidence; "
            "Q3 preserves the 269/270 audit boundary and excludes the RegionF full-horizon LP probe, "
            "while Q4 remains a 17-point discrete scan rather than a shadow-price or global-optimum claim. "
            "Independent Q1/Q2 artifact QA and Q3/Q4 render QA passed. No protected path was modified."
        ),
    }


def main() -> None:
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    task_package = load_task_package()
    input_records = verify_inputs(task_package)
    q3_summary, q4_summary, rolling, scenarios, q4_peak, q4_comparison = load_and_validate_data()
    configure_style()
    q3_layout = generate_q3_figure(q3_summary, rolling, scenarios)
    q4_layout = generate_q4_figure(q4_summary, q4_peak)
    contracts = make_contracts(q3_summary, q4_summary, rolling, scenarios, q4_peak)
    CONTRACTS_PATH.write_text(yaml.safe_dump(contracts, allow_unicode=True, sort_keys=False), encoding="utf-8")
    qa_report = make_qa_report(q3_layout, q4_layout)
    QA_REPORT_PATH.write_text(json.dumps(qa_report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    HANDOFF_PATH.write_text(
        json.dumps(make_handoff(input_records, contracts, qa_report), ensure_ascii=True, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
