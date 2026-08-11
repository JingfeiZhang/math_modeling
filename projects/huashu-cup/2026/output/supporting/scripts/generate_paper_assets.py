#!/usr/bin/env python3
"""Generate manuscript metric macros from frozen Problem C evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "paper" / "generated"


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tex_number(value: object, digits: int | None = None, percent: bool = False) -> str:
    if isinstance(value, bool):
        return "通过" if value else "未通过"
    if isinstance(value, int):
        return str(value)
    number = float(value)
    if digits is None:
        text = f"{number:.12g}"
    else:
        # Decimal values must remain parseable by siunitx; integer grouping is
        # configured in LaTeX and must not be embedded in generated macros.
        text = f"{number:.{digits}f}"
    return text + (r"\%" if percent else "")


def tex_scientific(value: object, digits: int = 2) -> str:
    text = f"{float(value):.{digits}e}"
    mantissa, exponent = text.split("e")
    return rf"${mantissa}\times 10^{{{int(exponent)}}}$"


def main() -> int:
    sources = {
        "q1_forecast": "experiments/C/Q1/q1-direct-20260808/models/forecast_q1/metrics_summary.json",
        "q1_schedule": "experiments/C/Q1/q1-direct-20260808/models/scheduling_q1/scheduling_metrics.json",
        "q1_robustness": "paper/generated/q1_robustness_summary.json",
        "q1_rolling_predictions": "sprints/sprint-20260807T130848306634Z/merged/forecast-q1/rolling_backtest_predictions.csv",
        "q2": "experiments/C/Q2/q2-full-compat-20260808/q2_compat_summary.json",
        "q2_policy_sensitivity": "experiments/C/Q2/q2-direct-20260808/sensitivity/q2_policy_sensitivity_summary.json",
        "q3": "experiments/C/Q3/q3-rolling-compat-20260808/q3_derived_summary.json",
        "q3_audit": "experiments/C/Q3/q3-full-audit-fix-20260809/summary.json",
        "q3_comparison": "experiments/C/Q3/q3-direct-20260808/models/rolling_milp/q3_comparison_summary.csv",
        "q3_adaptive": "experiments/C/Q3/q3-adaptive-window-20260809/q3_adaptive_summary.json",
        "q3_adaptive_comparison": "experiments/C/Q3/q3-adaptive-window-20260809/q3_adaptive_comparison.csv",
        "q4": "experiments/C/Q4/q4-optimization-20260809/q4_formal_summary.json",
        "q4_metrics": "experiments/C/Q4/q4-optimization-20260809/q4_joint_metrics.csv",
    }
    q1f = load_json(sources["q1_forecast"])
    q1s = load_json(sources["q1_schedule"])
    q1r = load_json(sources["q1_robustness"])
    with (ROOT / sources["q1_rolling_predictions"]).open(encoding="utf-8-sig", newline="") as handle:
        q1_rolling_rows = list(csv.DictReader(handle))
    q2 = load_json(sources["q2"])
    q2_policy = load_json(sources["q2_policy_sensitivity"])
    q3 = load_json(sources["q3"])
    q3a = load_json(sources["q3_audit"])
    with (ROOT / sources["q3_comparison"]).open(encoding="utf-8-sig", newline="") as handle:
        q3_comparison_rows = list(csv.DictReader(handle))
    q3_adaptive = load_json(sources["q3_adaptive"])
    with (ROOT / sources["q3_adaptive_comparison"]).open(encoding="utf-8-sig", newline="") as handle:
        q3_adaptive_comparison_rows = list(csv.DictReader(handle))
    q4 = load_json(sources["q4"])
    with (ROOT / sources["q4_metrics"]).open(encoding="utf-8-sig", newline="") as handle:
        q4_rows = list(csv.DictReader(handle))
    q4_index = {(row["scenario"], row["role"]): row for row in q4_rows}

    validation = q1f["summaries"]["validation"]
    blind = q1f["summaries"]["blind_test"]
    rolling = q1r["forecast"]["rolling_backtest"]
    sparse_series = q1r["forecast"]["sparse_series"]
    q2c = q2["comparison_vs_fifo"]
    q2r = q2["robustness"]
    q3r = q3["rolling_aggregate"]
    q3m = q3["rolling_binary_milp"]
    q1_origins = sorted({int(row["origin_hour"]) for row in q1_rolling_rows})
    q2_policy_rows = {row["policy_id"]: row for row in q2_policy["policy_results"]}
    q3_roll_rows = [row for row in q3_comparison_rows if row.get("evaluation") == "rolling_aggregate"]
    q3_adaptive_rows = {row["method_id"]: row for row in q3_adaptive_comparison_rows}

    metrics: dict[str, str] = {
        "q1-validation-baseline-wape": tex_number(validation["seasonal_baseline"]["system_weighted_wape"], 6),
        "q1-validation-main-wape": tex_number(validation["shared_hgbr_reconciled"]["system_weighted_wape"], 6),
        "q1-blind-baseline-wape": tex_number(blind["seasonal_baseline"]["system_weighted_wape"], 6),
        "q1-blind-baseline-rmse": tex_number(blind["seasonal_baseline"]["system_weighted_rmse_gpu_h"], 3),
        "q1-blind-main-rmse": tex_number(blind["shared_hgbr_reconciled"]["system_weighted_rmse_gpu_h"], 3),
        "q1-blind-baseline-width": tex_number(blind["seasonal_baseline"]["mean_interval_width_gpu_h"], 3),
        "q1-blind-main-width": tex_number(blind["shared_hgbr_reconciled"]["mean_interval_width_gpu_h"], 3),
        "q1-coherence-error": tex_scientific(q1f["checks"]["maximum_system_coherence_error_gpu_h"]),
        "q1-rolling-baseline-wape": tex_number(rolling["seasonal_baseline"]["system_weighted_wape"], 6),
        "q1-rolling-main-wape": tex_number(rolling["shared_hgbr_reconciled"]["system_weighted_wape"], 6),
        "q1-rolling-baseline-rmse": tex_number(rolling["seasonal_baseline"]["system_weighted_rmse_gpu_h"], 3),
        "q1-rolling-main-rmse": tex_number(rolling["shared_hgbr_reconciled"]["system_weighted_rmse_gpu_h"], 3),
        "q1-series-improved-count": tex_number(sum(row["main_wape"] <= row["baseline_wape"] for row in sparse_series)),
        "q1-series-low-coverage-count": tex_number(sum(row["main_coverage"] < 0.90 for row in sparse_series)),
        "q1-rolling-origin-count": tex_number(len(q1_origins)),
        "q1-rolling-origin-hours": "、".join(str(value) for value in q1_origins),
        "q1-task-count": tex_number(q1s["final_task_count"]),
        "q1-carry-count": tex_number(q1s["carry_in_count"]),
        "q1-solver-gap-pct": tex_number(100 * q1s["main"]["solver"]["optimality_gap"], 4, percent=True),
        "q1-solver-time-s": tex_number(q1s["main"]["solver"]["wall_time_seconds"], 3),
        "q2-fifo-cost": tex_number(q2c["baseline_cost_cny"], 3),
        "q2-main-cost": tex_number(q2c["candidate_cost_cny"], 3),
        "q2-fifo-carbon": tex_number(q2c["baseline_carbon_tco2"], 3),
        "q2-main-carbon": tex_number(q2c["candidate_carbon_tco2"], 3),
        "q2-fifo-latency": tex_number(q2c["baseline_mean_latency_ms"], 5),
        "q2-main-latency": tex_number(q2c["candidate_mean_latency_ms"], 5),
        "q2-fifo-renewable": tex_number(q2c["baseline_renewable_utilization_ratio"], 6),
        "q2-main-renewable": tex_number(q2c["candidate_renewable_utilization_ratio"], 6),
        "q2-operation-block-count": tex_number(q2r["operation_block_count"]),
        "q2-stress-probe-count": tex_number(q2r["fixed_schedule_stress_probe_count"]),
        "q2-block-cost-best-pct": tex_number(q2r["minimum_block_cost_change_pct"], 3),
        "q2-block-cost-worst-pct": tex_number(q2r["maximum_block_cost_change_pct"], 3),
        "q2-block-carbon-best-pct": tex_number(q2r["minimum_block_carbon_change_pct"], 3),
        "q2-block-carbon-worst-pct": tex_number(q2r["maximum_block_carbon_change_pct"], 3),
        "q3-baseline-cost": tex_number(q3r["baseline_cost_cny"], 3),
        "q3-main-cost": tex_number(q3r["candidate_cost_cny"], 3),
        "q3-baseline-carbon": tex_number(q3r["baseline_carbon_tco2"], 6),
        "q3-main-carbon": tex_number(q3r["candidate_carbon_tco2"], 6),
        "q3-max-mip-gap": tex_scientific(q3m["maximum_mip_gap"]),
        "q3-load-residual": tex_scientific(q3["load_recomputation"]["maximum_facility_residual_mw"]),
        "q3-audits-passed": tex_number(q3a["audit_boundary"]["total_audits_passed"]),
        "q3-audits-total": tex_number(q3a["audit_boundary"]["total_audit_count"]),
        "q3-adaptive-cost-delta": tex_number(q3_adaptive["result"]["cost_saving_vs_fixed168_CNY"], 3),
        "q3-adaptive-renewable-gain": tex_number(q3_adaptive["result"]["renewable_gain_vs_fixed168"], 8),
        "q3-adaptive-block-count-168": tex_number(q3_adaptive["result"]["horizon_counts"].get("168", 0)),
        "q3-adaptive-block-count-192": tex_number(q3_adaptive["result"]["horizon_counts"].get("192", 0)),
        "q3-adaptive-block-count-31": tex_number(q3_adaptive["result"]["horizon_counts"].get("31", 0)),
        "q4-accepted-moves": tex_number(q4["search"]["accepted_task_moves"]),
        "q4-storage-evals": tex_number(q4["search"]["storage_evaluations"]),
        "q4-scenario-count": tex_number(q4["scope"]["scenario_count"]),
        "q4-observed-renewable-gain": tex_number(q4["observed_72h"]["renewable_utilization_gain"], 6),
        "q4-low-renewable-gain": tex_number(q4["low_renewable_72h"]["renewable_utilization_gain"], 6),
        "q4-joint-cost-delta": tex_number(q4["joint_stress_72h"]["cost_delta_CNY"], 3),
    }
    scenario_aliases = {
        "obs": "observed",
        "low": "renewable_low_empirical",
        "joint": "joint_stress",
    }
    for alias, scenario in scenario_aliases.items():
        for role_alias, role in (("base", "sequential_baseline"), ("main", "joint_candidate")):
            row = q4_index[(scenario, role)]
            metrics[f"q4-{alias}-{role_alias}-cost"] = tex_number(row["cost_CNY"], 3)
            metrics[f"q4-{alias}-{role_alias}-carbon"] = tex_number(row["carbon_tCO2"], 6)
            metrics[f"q4-{alias}-{role_alias}-renew"] = tex_number(row["renewable_utilization_ratio"], 6)

    # Diagnostic robustness values are read-only derivations. Positive peak
    # means max(0, net grid import), so an export peak is never misreported as
    # a purchase reduction.
    for row in q3_roll_rows:
        region = row["region"].lower()
        base_peak = max(0.0, float(row["peak_net_import_MW_baseline"]))
        cand_peak = max(0.0, float(row["peak_net_import_MW_candidate"]))
        base_std = float(row["load_std_MW_baseline"])
        cand_std = float(row["load_std_MW_candidate"])
        metrics[f"q3-peak-{region}-baseline"] = tex_number(base_peak, 3)
        metrics[f"q3-peak-{region}-candidate"] = tex_number(cand_peak, 3)
        metrics[f"q3-peak-{region}-delta"] = tex_number(cand_peak - base_peak, 3)
        metrics[f"q3-std-{region}-baseline"] = tex_number(base_std, 3)
        metrics[f"q3-std-{region}-candidate"] = tex_number(cand_std, 3)
        metrics[f"q3-std-{region}-delta"] = tex_number(cand_std - base_std, 3)

    # Q2 policy sensitivity intentionally omits the stale renewable ratio in
    # that diagnostic file; the formal Q2 denominator is reported elsewhere.
    for policy_id, row in q2_policy_rows.items():
        safe_id = policy_id.replace("-", "_")
        metrics[f"q2-policy-{safe_id}-cost-delta-pct"] = tex_number(row["cost_change_pct_vs_current"], 3)
        metrics[f"q2-policy-{safe_id}-carbon-delta-pct"] = tex_number(row["carbon_change_pct_vs_current"], 3)
        metrics[f"q2-policy-{safe_id}-latency-delta-pct"] = tex_number(row["latency_change_pct_vs_current"], 3)
        metrics[f"q2-policy-{safe_id}-hard-audit"] = tex_number(bool(row["hard_audit_passed"]))
        metrics[f"q2-policy-{safe_id}-eligible"] = tex_number(bool(row["eligible_for_root_review"]))

    for method_id, row in q3_adaptive_rows.items():
        safe_id = method_id.replace("-", "_")
        metrics[f"q3-window-{safe_id}-cost"] = tex_number(row["total_cost_CNY"], 3)
        metrics[f"q3-window-{safe_id}-renew"] = tex_number(row["mean_region_renewable_utilization_ratio"], 6)

    GENERATED.mkdir(parents=True, exist_ok=True)
    lines = [
        "% Generated from frozen evidence. Do not edit.",
        r"\providecommand{\PaperMetric}[1]{\csname paperdraftmetric@#1\endcsname}",
    ]
    for key in sorted(metrics):
        lines.append(rf"\expandafter\def\csname paperdraftmetric@{key}\endcsname{{{metrics[key]}}}")
    (GENERATED / "paper_metrics.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "problem_id": "C",
        "generated_file": "paper/generated/paper_metrics.tex",
        "generated_sha256": sha256(GENERATED / "paper_metrics.tex"),
        "sources": [
            {"path": relative, "sha256": sha256(ROOT / relative)}
            for relative in sources.values()
        ],
        "metric_keys": sorted(metrics),
        "derived_field_locators": [
            {
                "metric_prefix": "q1-rolling-origin",
                "source": sources["q1_rolling_predictions"],
                "selector": "unique(origin_hour)",
                "unit": "h",
            },
            {
                "metric_prefix": "q2-policy",
                "source": sources["q2_policy_sensitivity"],
                "selector": "policy_results[*].{cost_change_pct_vs_current,carbon_change_pct_vs_current,latency_change_pct_vs_current,hard_audit_passed,eligible_for_root_review}",
                "unit": "%, %, %, boolean, boolean",
            },
            {
                "metric_prefix": "q3-peak|q3-std",
                "source": sources["q3_comparison"],
                "selector": "evaluation=rolling_aggregate; region; peak_net_import_MW_*; load_std_MW_*",
                "transformation": "positive_peak=max(0, net_import); std_delta=candidate-baseline",
                "unit": "MW",
            },
            {
                "metric_prefix": "q3-window",
                "source": sources["q3_adaptive_comparison"],
                "selector": "method_id; total_cost_CNY; mean_region_renewable_utilization_ratio",
                "unit": "CNY, ratio",
            },
        ],
        "manual_values_forbidden": True,
    }
    (GENERATED / "paper_metrics_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
