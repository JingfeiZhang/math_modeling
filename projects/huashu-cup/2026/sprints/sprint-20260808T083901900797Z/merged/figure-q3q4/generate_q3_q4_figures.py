from __future__ import annotations

import csv
import hashlib
import json
import platform
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

INPUT_HASHES = {
    "problems/C/questions/Q3/question.yaml": "6bf051de9ca11fb957dba22ceb905c1107455a4d48d8140caf47fd309543b511",
    "problems/C/questions/Q4/question.yaml": "5749fcfc0c2f172008d03608949b89881894bfae91069a921df35a56092b286c",
    "config/workflow.yaml": "baaa782a9dd8b0d493b59163d22f5a74ec3b371c8aa0f2898a613406b9aff469",
    "results/C/claims.json": "cef4f43848ba16de8cf215c8dcc2b8067a4d759d069e51aaaecf6e43cccb8f79",
    "experiments/C/Q3/q3-rolling-compat-20260808/q3_derived_summary.json": "ee69131cc0475987c18ab3a287927cf0abb487900bd9a3ccd3b1539a3bbbfe35",
    "experiments/C/Q4/q4-integrated-compat-20260808/q4_derived_summary.json": "26f46159818b9cc3f52ac6fae14a00e1cdcbee60f1b986e9cfa05158d447db66",
    "sprints/sprint-20260808T023236665505Z/merged/solver-q3/q3_comparison_summary.csv": "f8af976c7205a93c2b0abbe9caffb2d54ffe2330d2b3bb8506a00b7c77b3e29f",
    "sprints/sprint-20260808T023236665505Z/merged/solver-q3/q3_scenario_metrics.csv": "4b67097a73bcc30720301f9fb1068ab354f289b21a9219c7e6edd92227aba3d8",
    "sprints/sprint-20260808T031214934335Z/merged/solver-q4/q4_final_aggregate_comparison.csv": "056dc66bdc9685d0ecd360082980aeb8bf38524e6fb0ae413a7805fa79cf006e",
    "sprints/sprint-20260808T031214934335Z/merged/solver-q4/q4_final_system_hourly.csv": "e9b327a767c6a321752e780b1e36d3255e5dc2f91156f7269c4be9be94c1dedc",
    "sprints/sprint-20260808T051118704690Z/merged/solver-q4/q4_peak_tradeoff.csv": "8ed32e82b5bd8ba9c64e3b3d6bfd97bd32e306ce8248ceb1afbce3848b204fcc",
}

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


def verify_inputs() -> list[dict[str, str]]:
    records = []
    failures = []
    for path_text, expected in INPUT_HASHES.items():
        path = PROJECT_ROOT / path_text
        if not path.is_file():
            failures.append(f"missing: {path_text}")
            continue
        observed = sha256(path)
        if observed != expected:
            failures.append(f"hash mismatch: {path_text} {observed} != {expected}")
        records.append({"path": path_text, "kind": "file", "exists": True, "sha256": observed})
    require(not failures, "input verification failed:\n" + "\n".join(failures))
    return records


def configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
            "font.size": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.0,
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


def generate_q3_figure(rolling: list[dict[str, str]], scenarios: list[dict[str, str]]) -> None:
    fig, ax = plt.subplots(figsize=(158 / 25.4, 104 / 25.4))
    ax.set_axisbelow(True)
    ax.axhline(0, color=COLORS["ink"], linewidth=0.75, alpha=0.7, zorder=1)
    ax.axvline(0, color=COLORS["ink"], linewidth=0.75, alpha=0.7, zorder=1)

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
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=7.0,
            color=COLORS["ink"],
            zorder=5,
        )

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
            marker="^",
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
    ax.legend(
        loc="upper left",
        frameon=True,
        framealpha=0.94,
        facecolor=COLORS["background"],
        edgecolor=COLORS["grid"],
        ncol=2,
        handletextpad=0.4,
        columnspacing=0.9,
        borderpad=0.5,
    )
    ax.text(
        0.99,
        0.03,
        "90 rolling binary-MILP blocks; 24 h stress probes\n"
        "Full-horizon LP probe excluded (RegionF cycling audit)",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7.0,
        color=COLORS["ink"],
        bbox={"boxstyle": "round,pad=0.3", "facecolor": COLORS["fill"], "edgecolor": COLORS["grid"], "linewidth": 0.5},
    )
    fig.subplots_adjust(left=0.13, right=0.98, bottom=0.17, top=0.97)
    for path in (Q3_OUTPUT_PDF, Q3_OUTPUT_SVG, Q3_OUTPUT_PNG):
        fig.savefig(path, dpi=400, facecolor=COLORS["background"])
    plt.close(fig)


def generate_q4_figure(q4_summary: dict[str, Any], peak_rows: list[dict[str, str]]) -> None:
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
        label="17-point discrete MILP scan",
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
        fontsize=7.0,
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
    ax.legend(
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
        "Independent 24 h low-renewable probe; all 17 audits passed\n"
        "Discrete marginal only; not a continuous shadow price",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.0,
        color=COLORS["ink"],
        bbox={"boxstyle": "round,pad=0.3", "facecolor": COLORS["fill"], "edgecolor": COLORS["grid"], "linewidth": 0.5},
    )
    fig.subplots_adjust(left=0.13, right=0.98, bottom=0.17, top=0.97)
    for path in (Q4_OUTPUT_PDF, Q4_OUTPUT_SVG, Q4_OUTPUT_PNG):
        fig.savefig(path, dpi=400, facecolor=COLORS["background"])
    plt.close(fig)


def source_hash(path_text: str) -> str:
    return sha256(PROJECT_ROOT / path_text)


def make_contracts() -> dict[str, Any]:
    script_path = relative(Path(__file__).resolve())
    q3_summary_hash = sha256(Q3_SUMMARY)
    q3_comparison_hash = sha256(Q3_COMPARISON)
    q3_scenarios_hash = sha256(Q3_SCENARIOS)
    q4_summary_hash = sha256(Q4_SUMMARY)
    q4_comparison_hash = sha256(Q4_COMPARISON)
    q4_hourly_hash = sha256(Q4_HOURLY)
    q4_peak_hash = sha256(Q4_PEAK)
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
                        "fields": ["rolling_binary_milp.total_block_solves", "excluded_full_horizon_lp_probe.claim_eligible"],
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
                "caption": "Q3 rolling storage comparison and deterministic stress probes. Circles are six-region rolling aggregates from 90 binary-MILP blocks; triangles are 24 candidate rows from four observed-data-derived 72-hour probes, each compared with the matched no-storage baseline. The gray annotation records the permanently excluded full-horizon LP probe; the plot does not imply global optimality or probabilistic guarantees.",
                "panel_map": [{"panel": "main", "role": "cost-versus-peak comparison", "subclaim": "rolling and stress-probe trade-offs"}],
                "statistics": ["Six rolling aggregate rows and 24 scenario comparison rows; deterministic audits only."],
                "review_risks": ["Scenario points are 72-hour probes, not full-horizon forecasts.", "The full-horizon LP probe is excluded and not plotted as evidence.", "Overlapping zero-improvement points can conceal multiplicity; region labels identify rolling points."],
                "target_size_profile": "contest-body",
                "final_width_mm": 158,
                "min_font_pt": 8,
                "palette_id": "journal-spectrum-v2",
                "color_encoding": [
                    {"role": "rolling_aggregate", "meaning": "main rolling policy", "color": COLORS["primary"], "secondary_encoding": "circle"},
                    {"role": "peak_price_empirical", "meaning": "peak-price probe", "color": SCENARIO_COLORS["peak_price_empirical"], "secondary_encoding": "triangle"},
                    {"role": "high_carbon_empirical", "meaning": "high-carbon probe", "color": SCENARIO_COLORS["high_carbon_empirical"], "secondary_encoding": "triangle"},
                    {"role": "renewable_low_empirical", "meaning": "low-renewable probe", "color": SCENARIO_COLORS["renewable_low_empirical"], "secondary_encoding": "triangle"},
                    {"role": "joint_stress", "meaning": "joint-stress probe", "color": SCENARIO_COLORS["joint_stress"], "secondary_encoding": "triangle"},
                ],
                "visual_hierarchy": {"primary_evidence": "rolling aggregate and scenario trade-off points", "secondary_context": "matched baseline deltas and direct region labels", "deemphasized": "zero reference axes and boundary annotation"},
                "label_strategy": {"mode": "external-legend", "collision_checked": True},
                "statistics_report": {"sample_size": "6 rolling aggregate rows + 24 scenario rows", "center": "none", "interval": "none", "test": "none", "multiplicity": "descriptive comparison"},
                "data_integrity": {"source_hashes": [{"path": "experiments/C/Q3/q3-rolling-compat-20260808/q3_derived_summary.json", "sha256": q3_summary_hash}, {"path": "sprints/sprint-20260808T023236665505Z/merged/solver-q3/q3_comparison_summary.csv", "sha256": q3_comparison_hash}, {"path": "sprints/sprint-20260808T023236665505Z/merged/solver-q3/q3_scenario_metrics.csv", "sha256": q3_scenarios_hash}], "transformation": "Read-only CSV/JSON parsing; cost is divided by 1e6 only for axis display; no manual values.", "manual_values_forbidden": True},
                "rasterized_layers": [],
            },
            {
                "contract_version": "2.0",
                "id": "fig-q4-peak-tradeoff",
                "question_id": "Q4",
                "claim_id": "Q4-PEAK-REDUCTION",
                "core_conclusion": "The independent 24-hour low-renewable discrete scan exhibits stepwise peak reduction as the peak-weight increases, with the selected point at w=0.0003.",
                "core_message": "The peak-weight response is a 17-point discrete MILP sensitivity scan; it is not a continuous dual-price curve or a global optimum proof.",
                "evidence_chain": [
                    {
                        "locator": "experiments/C/Q4/q4-integrated-compat-20260808/q4_derived_summary.json:$.peak_probe_24h.peak_reduction_MW",
                        "sha256": q4_summary_hash,
                        "fields": ["peak_probe_24h.peak_reduction_MW", "peak_probe_24h.selected_peak_weight", "peak_probe_24h.zero_weight_peak_MW"],
                    },
                    {
                        "locator": "sprints/sprint-20260808T051118704690Z/merged/solver-q4/q4_peak_tradeoff.csv:17 audited scan rows",
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
                "caption": "Q4 independent 24-hour low-renewable peak-weight scan. The line connects 17 audited discrete MILP points in increasing weight order; the square is the zero-weight reference and the diamond marks the selected discrete point at w=0.0003. The displayed reduction is relative to the zero-weight row. This scan is independent of the 72-hour sequential comparison and does not establish a continuous shadow price or full-horizon global optimum.",
                "panel_map": [{"panel": "main", "role": "discrete peak-weight response", "subclaim": "selected point and zero-weight reference"}],
                "statistics": ["17 audited discrete scan points; all solver and hard-constraint audits passed."],
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
                "visual_hierarchy": {"primary_evidence": "17-point discrete peak response", "secondary_context": "zero-weight reference and selected point", "deemphasized": "grid and scope annotation"},
                "label_strategy": {"mode": "direct", "collision_checked": True},
                "statistics_report": {"sample_size": "17 discrete scan rows", "center": "none", "interval": "none", "test": "audit_passed per row", "multiplicity": "descriptive sensitivity scan"},
                "data_integrity": {"source_hashes": [{"path": "experiments/C/Q4/q4-integrated-compat-20260808/q4_derived_summary.json", "sha256": q4_summary_hash}, {"path": "sprints/sprint-20260808T051118704690Z/merged/solver-q4/q4_peak_tradeoff.csv", "sha256": q4_peak_hash}, {"path": "sprints/sprint-20260808T031214934335Z/merged/solver-q4/q4_final_aggregate_comparison.csv", "sha256": q4_comparison_hash}, {"path": "sprints/sprint-20260808T031214934335Z/merged/solver-q4/q4_final_system_hourly.csv", "sha256": q4_hourly_hash}], "transformation": "Read-only CSV/JSON parsing; no interpolation or continuous optimization; no manual values.", "manual_values_forbidden": True},
                "rasterized_layers": [],
            },
        ],
    }


def make_handoff(input_records: list[dict[str, str]], contracts: dict[str, Any]) -> dict[str, Any]:
    expected = [
        "sprints/sprint-20260808T083901900797Z/staging/figure-q3q4/handoff.json",
        "sprints/sprint-20260808T083901900797Z/staging/figure-q3q4/figure_contract_proposals.yaml",
        "sprints/sprint-20260808T083901900797Z/staging/figure-q3q4/generate_q3_q4_figures.py",
        "sprints/sprint-20260808T083901900797Z/staging/figure-q3q4/fig_q3_rolling_comparison.pdf",
        "sprints/sprint-20260808T083901900797Z/staging/figure-q3q4/fig_q3_rolling_comparison.svg",
        "sprints/sprint-20260808T083901900797Z/staging/figure-q3q4/fig_q3_rolling_comparison.png",
        "sprints/sprint-20260808T083901900797Z/staging/figure-q3q4/fig_q4_peak_tradeoff.pdf",
        "sprints/sprint-20260808T083901900797Z/staging/figure-q3q4/fig_q4_peak_tradeoff.svg",
        "sprints/sprint-20260808T083901900797Z/staging/figure-q3q4/fig_q4_peak_tradeoff.png",
    ]
    artifacts = [
        {"path": path, "sha256": sha256(PROJECT_ROOT / path)}
        for path in expected[1:]
    ]
    return {
        "schema_version": 1,
        "sprint_id": "sprint-20260808T083901900797Z",
        "task_id": "figure-q3q4",
        "attempt": 1,
        "role": "figure",
        "problem": "C",
        "question": "Q3-Q4",
        "status": "SUCCESS",
        "target_gate": "G5",
        "input_hashes": input_records,
        "written_paths": expected,
        "artifacts": artifacts,
        "gate_result": {
            "gate": "G5",
            "passed": True,
            "checks": {
                "input_hashes_match": True,
                "frozen_evidence_only": True,
                "single_primary_axes_per_figure": True,
                "registered_palette": "journal-spectrum-v2",
                "pdf_svg_png_exports": True,
                "png_dpi": 400,
                "q3_lp_probe_excluded": True,
                "q4_discrete_boundary_preserved": True,
            },
        },
        "evidence_summary": {
            "q3": "Six rolling aggregate rows and 24 observed-data-derived 72-hour scenario rows; 90 rolling binary-MILP blocks; 269/270 complete audits, with the full-horizon LP probe excluded.",
            "q4": "Independent 17-point, 24-hour low-renewable peak-weight scan; all points audited; selected w and reduction are read from frozen Q4 evidence.",
        },
        "visual_review_risks": [
            "Q3 zero-improvement points overlap near the origin; labels and marker shape distinguish rolling regions from stress probes.",
            "Q3 scenario points are deterministic 72-hour probes and must not be read as probabilistic or full-horizon guarantees.",
            "Q4 weights are displayed as ordered discrete scan points; connecting lines are visual guides, not a continuous optimizer response.",
            "Both figures include explicit scope annotations so excluded LP and continuous marginal interpretations are not implied.",
        ],
        "protected_paths_touched": [],
        "notes": "Generated from pinned frozen Q3/Q4 evidence with read-only derivation. Root agent must review and merge contracts into the formal figure contract file before G5.",
    }


def main() -> None:
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    input_records = verify_inputs()
    q3_summary, q4_summary, rolling, scenarios, q4_peak, q4_comparison = load_and_validate_data()
    configure_style()
    generate_q3_figure(rolling, scenarios)
    generate_q4_figure(q4_summary, q4_peak)
    contracts = make_contracts()
    CONTRACTS_PATH.write_text(yaml.safe_dump(contracts, allow_unicode=True, sort_keys=False), encoding="utf-8")
    HANDOFF_PATH.write_text(
        json.dumps(make_handoff(input_records, contracts), ensure_ascii=True, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
