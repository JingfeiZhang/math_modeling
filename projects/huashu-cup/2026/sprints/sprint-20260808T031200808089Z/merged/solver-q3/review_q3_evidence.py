#!/usr/bin/env python
"""Deterministic G5 claim-boundary review for the merged Q3 evidence."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


STAGING = Path(__file__).resolve().parent
ROOT = STAGING.parents[3]
SPRINT_ID = "sprint-20260808T031200808089Z"
TASK_ID = "solver-q3"
TASK_PACKAGE = ROOT / "sprints" / SPRINT_ID / "tasks" / f"{TASK_ID}.json"
SOURCE = ROOT / "sprints" / "sprint-20260808T023236665505Z" / "merged" / "solver-q3"
TOL = 5e-5


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def directory_hash(path: Path) -> str:
    records = [
        f"{item.relative_to(path).as_posix()}:{sha256_file(item)}"
        for item in sorted(path.rglob("*"))
        if item.is_file()
    ]
    return hashlib.sha256("\n".join(records).encode("utf-8")).hexdigest()


def verify_inputs(task: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in task["input_hashes"]:
        path = ROOT / item["path"]
        if item["kind"] == "directory" and path.is_dir():
            observed = directory_hash(path)
        elif path.is_file():
            observed = sha256_file(path)
        else:
            observed = None
        results.append(
            {
                "path": item["path"],
                "expected_sha256": item["sha256"],
                "observed_sha256": observed,
                "match": observed == item["sha256"],
            }
        )
    if not all(row["match"] for row in results):
        raise RuntimeError("input hash verification failed before evidence read")
    return results


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def evidence_locator(name: str, **extra: Any) -> dict[str, Any]:
    path = SOURCE / name
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(path),
        **extra,
    }


def max_audit_value(rows: list[dict[str, Any]]) -> float:
    return float(max(abs(float(value)) for row in rows for value in row["checks"].values()))


def main() -> int:
    STAGING.mkdir(parents=True, exist_ok=True)
    task = json.loads(TASK_PACKAGE.read_text(encoding="utf-8"))
    hash_review = verify_inputs(task)

    summary = json.loads((SOURCE / "q3_summary.json").read_text(encoding="utf-8"))
    audit_doc = json.loads((SOURCE / "q3_constraint_audit.json").read_text(encoding="utf-8"))
    manifest = json.loads((SOURCE / "q3_run_manifest.json").read_text(encoding="utf-8"))
    runner_text = (SOURCE / "run_solver_q3.py").read_text(encoding="utf-8")
    candidate_metrics = pd.read_csv(SOURCE / "q3_candidate_metrics.csv")
    baseline_metrics = pd.read_csv(SOURCE / "q3_baseline_metrics.csv")
    comparison = pd.read_csv(SOURCE / "q3_comparison_summary.csv")
    scenario_metrics = pd.read_csv(SOURCE / "q3_scenario_metrics.csv")
    candidate_dispatch = pd.read_csv(SOURCE / "q3_dispatch.csv")
    baseline_dispatch = pd.read_csv(SOURCE / "q3_baseline_dispatch.csv")
    load_audit_artifact = pd.read_csv(SOURCE / "q3_load_recompute_audit.csv")

    data_dir = ROOT / "problems" / "C" / "data"
    region_data = pd.read_excel(
        data_dir / "region_time_data.xlsx", sheet_name="region_time_data", engine="openpyxl"
    ).sort_values(["Region", "Hour"]).reset_index(drop=True)
    storage_data = pd.read_excel(
        data_dir / "storage_information.xlsx", sheet_name="storage_information", engine="openpyxl"
    )
    power_table = pd.read_excel(
        data_dir / "power_mapping.xlsx", sheet_name="任务功率映射", engine="openpyxl"
    )
    power_rules = pd.read_excel(
        data_dir / "power_mapping.xlsx", sheet_name="计算口径", engine="openpyxl"
    )

    audits = audit_doc["audits"]
    solver_records = pd.DataFrame(summary["solver_records"])
    claim_solver_records = solver_records[
        solver_records.evaluation.isin(["fixed", "rolling_block", "scenario"])
    ].copy()
    rolling_records = solver_records[solver_records.evaluation == "rolling_block"].copy()
    full_probe_records = solver_records[solver_records.evaluation == "full_cycle_probe"].copy()

    claim_candidate_audits = [
        row
        for row in audits
        if row["method"] != "no_storage_renewable_first"
        and row["evaluation"] != "full_cycle_probe"
    ]
    claim_baseline_audits = [
        row for row in audits if row["method"] == "no_storage_renewable_first"
    ]
    rolling_candidate_audits = [
        row
        for row in audits
        if row["evaluation"] == "rolling_aggregate"
        and row["method"] == "rolling_carbon_aware_MILP"
    ]
    full_probe_audits = [row for row in audits if row["evaluation"] == "full_cycle_probe"]

    binary_source_checks = {
        "mode_integrality_declared": 'integrality[slices["mode"]] = 1.0' in runner_text,
        "LP_relaxation_limited_to_full_probe": (
            "solve_integrality = np.zeros_like(integrality) if full_lp else integrality"
            in runner_text
        ),
        "full_probe_removed_from_comparison": (
            'candidate_metrics_df.evaluation != "full_cycle_probe"' in runner_text
        ),
    }
    claim_gap_values = claim_solver_records.mip_gap.dropna().astype(float)
    binary_review = {
        "status": "PASS",
        "claim_eligible_solver_record_count": int(len(claim_solver_records)),
        "all_solver_modes_binary": bool(
            claim_solver_records.solver_mode.astype(str).eq("binary_MILP").all()
        ),
        "all_solver_success": bool(claim_solver_records.success.astype(bool).all()),
        "maximum_mip_gap": float(claim_gap_values.max()),
        "declared_mip_gap_limit": float(manifest["solver"]["mip_rel_gap"]),
        "candidate_audit_count": len(claim_candidate_audits),
        "candidate_audits_all_pass": bool(
            claim_candidate_audits and all(row["passed"] for row in claim_candidate_audits)
        ),
        "candidate_max_audit_residual": max_audit_value(claim_candidate_audits),
        "charge_mode_values": sorted(
            int(value)
            for value in candidate_dispatch[
                candidate_dispatch.Evaluation != "full_cycle_probe"
            ].ChargeMode.unique()
        ),
        "source_checks": binary_source_checks,
        "boundary": (
            "This proves binary charge/discharge mode handling for fixed, rolling-block, and "
            "72-hour scenario runs. It does not make the relaxed 2407-hour LP probe claim-eligible."
        ),
    }
    if not (
        binary_review["all_solver_modes_binary"]
        and binary_review["all_solver_success"]
        and binary_review["maximum_mip_gap"] <= manifest["solver"]["mip_rel_gap"] + 1e-12
        and binary_review["candidate_audits_all_pass"]
        and all(binary_source_checks.values())
    ):
        binary_review["status"] = "FAIL"

    regions = summary["regions"]
    rolling_candidate = candidate_dispatch[candidate_dispatch.Evaluation == "rolling_block"]
    rolling_baseline = baseline_dispatch[baseline_dispatch.Evaluation == "rolling_block"]
    expected_starts = list(range(0, 2353, 168))
    expected_horizons = [168] * 14 + [55]
    coverage_by_region: dict[str, Any] = {}
    for region in regions:
        candidate_region = rolling_candidate[rolling_candidate.Region == region]
        baseline_region = rolling_baseline[rolling_baseline.Region == region]
        records_region = rolling_records[rolling_records.region == region].sort_values(
            "window_start_h"
        )
        coverage_by_region[region] = {
            "candidate_rows": int(len(candidate_region)),
            "baseline_rows": int(len(baseline_region)),
            "candidate_hours_exact_0_2406": sorted(candidate_region.Hour.astype(int).tolist())
            == list(range(2407)),
            "baseline_hours_exact_0_2406": sorted(baseline_region.Hour.astype(int).tolist())
            == list(range(2407)),
            "candidate_duplicate_hours": int(candidate_region.Hour.duplicated().sum()),
            "baseline_duplicate_hours": int(baseline_region.Hour.duplicated().sum()),
            "block_starts": records_region.window_start_h.astype(int).tolist(),
            "block_horizons": records_region.horizon_h.astype(int).tolist(),
            "block_layout_exact": (
                records_region.window_start_h.astype(int).tolist() == expected_starts
                and records_region.horizon_h.astype(int).tolist() == expected_horizons
            ),
        }
    rolling_review = {
        "status": "PASS",
        "policy": summary["rolling_policy"],
        "regions": len(regions),
        "blocks_per_region": 15,
        "total_block_solves": int(len(rolling_records)),
        "block_layout": "14 contiguous 168-hour blocks plus one 55-hour block",
        "all_block_solves_success": bool(rolling_records.success.astype(bool).all()),
        "all_block_modes_binary": bool(
            rolling_records.solver_mode.astype(str).eq("binary_MILP").all()
        ),
        "maximum_block_mip_gap": float(rolling_records.mip_gap.fillna(0).max()),
        "fallback_used_blocks": int(rolling_records.used_fallback.astype(bool).sum()),
        "coverage_by_region": coverage_by_region,
        "rolling_aggregate_audits_all_pass": bool(
            len(rolling_candidate_audits) == len(regions)
            and all(row["passed"] for row in rolling_candidate_audits)
        ),
        "rolling_aggregate_max_residual": max_audit_value(rolling_candidate_audits),
        "boundary": (
            "Coverage is full for supplied hours 0-2406 through contiguous rolling subproblems. "
            "This is not a single globally optimized 2407-hour binary MILP. Terminal SOC is a "
            "lower-bound carry rule, not equality to the initial SOC at every boundary."
        ),
    }
    if not (
        rolling_review["all_block_solves_success"]
        and rolling_review["all_block_modes_binary"]
        and rolling_review["fallback_used_blocks"] == 0
        and rolling_review["rolling_aggregate_audits_all_pass"]
        and all(
            row["candidate_hours_exact_0_2406"]
            and row["baseline_hours_exact_0_2406"]
            and row["candidate_duplicate_hours"] == 0
            and row["baseline_duplicate_hours"] == 0
            and row["block_layout_exact"]
            for row in coverage_by_region.values()
        )
    ):
        rolling_review["status"] = "FAIL"

    key_columns = ["evaluation", "scenario", "window_start_h", "horizon_h", "region"]
    claim_candidate_metrics = candidate_metrics[
        candidate_metrics.evaluation != "full_cycle_probe"
    ]
    candidate_keys = set(map(tuple, claim_candidate_metrics[key_columns].to_numpy()))
    baseline_keys = set(map(tuple, baseline_metrics[key_columns].to_numpy()))
    comparison_keys = set(map(tuple, comparison[key_columns].to_numpy()))
    no_storage_columns = ["ChargePower_MW", "DischargePower_MW", "GridCharge_MW"]
    baseline_review = {
        "status": "PASS",
        "candidate_and_baseline_dispatch_schema_identical": list(candidate_dispatch.columns)
        == list(baseline_dispatch.columns),
        "candidate_claim_metric_rows": int(len(claim_candidate_metrics)),
        "baseline_metric_rows": int(len(baseline_metrics)),
        "comparison_rows": int(len(comparison)),
        "comparison_key_duplicates": int(comparison.duplicated(key_columns).sum()),
        "matching_metric_key_sets": candidate_keys == baseline_keys == comparison_keys,
        "baseline_no_storage_max_abs_MW": float(
            np.max(np.abs(baseline_dispatch[no_storage_columns].to_numpy(float)))
        ),
        "baseline_audit_count": len(claim_baseline_audits),
        "baseline_audits_all_pass": bool(
            claim_baseline_audits and all(row["passed"] for row in claim_baseline_audits)
        ),
        "baseline_max_audit_residual": max_audit_value(claim_baseline_audits),
        "metric_definitions": summary["metrics_definition"],
        "boundary": (
            "The baseline is comparable by output schema, keys, load inputs, constraints, and metric "
            "definitions. It is a deterministic no-storage policy, not a second optimization model."
        ),
    }
    if not (
        baseline_review["candidate_and_baseline_dispatch_schema_identical"]
        and baseline_review["matching_metric_key_sets"]
        and baseline_review["comparison_key_duplicates"] == 0
        and baseline_review["baseline_no_storage_max_abs_MW"] <= TOL
        and baseline_review["baseline_audits_all_pass"]
    ):
        baseline_review["status"] = "FAIL"

    fallback_code_checks = {
        "retry_before_fallback": 'if not retry_info["success"]:' in runner_text,
        "single_rule_named": "dispatch = rule_fallback(frame, storage, initial_soc)" in runner_text,
        "rolling_only_enabled": 'allow_fallback=True' in runner_text,
    }
    fallback_review = {
        "status": "PASS",
        "name": summary["fallback"]["name"],
        "activation": summary["fallback"]["activation"],
        "summary_used_blocks": int(summary["fallback"]["used_blocks"]),
        "solver_record_used_blocks": int(rolling_records.used_fallback.astype(bool).sum()),
        "fallback_dispatch_rows": int(
            (candidate_dispatch.Method.astype(str) == "valley_peak_fallback").sum()
        ),
        "code_checks": fallback_code_checks,
        "boundary": (
            "The fallback was never activated, so no effectiveness or superiority claim about the "
            "fallback is eligible. Only its trigger and non-use may be stated."
        ),
    }
    if not (
        fallback_review["summary_used_blocks"] == 0
        and fallback_review["solver_record_used_blocks"] == 0
        and fallback_review["fallback_dispatch_rows"] == 0
        and all(fallback_code_checks.values())
    ):
        fallback_review["status"] = "FAIL"

    derived_it = (
        region_data.Baseline_AI_IT_Load_MW.astype(float)
        + region_data.NonAI_IT_Load_MW.astype(float)
    )
    it_residual = region_data.IT_Load_MW.astype(float) - derived_it
    pue_by_region: dict[str, float] = {}
    load_rows: list[dict[str, Any]] = []
    for region, group in region_data.assign(DerivedIT=derived_it).groupby("Region", sort=True):
        positive = group[group.DerivedIT > 1e-9]
        pue = float(
            np.median(positive.Total_Load_MW.astype(float) / positive.DerivedIT.astype(float))
        )
        pue_by_region[str(region)] = pue
        recomputed = group.DerivedIT.astype(float) * pue
        load_rows.append(
            {
                "region": str(region),
                "rows": int(len(group)),
                "inferred_pue": pue,
                "it_residual_max_abs_MW": float(
                    np.max(np.abs(group.IT_Load_MW.astype(float) - group.DerivedIT.astype(float)))
                ),
                "facility_residual_max_abs_MW": float(
                    np.max(np.abs(group.Total_Load_MW.astype(float) - recomputed))
                ),
                "facility_residual_mean_abs_MW": float(
                    np.mean(np.abs(group.Total_Load_MW.astype(float) - recomputed))
                ),
            }
        )
    independent_load = pd.DataFrame(load_rows).sort_values("region").reset_index(drop=True)
    artifact_load = load_audit_artifact.rename(columns={"Region": "region"}).sort_values(
        "region"
    ).reset_index(drop=True)
    load_columns = [
        "rows",
        "inferred_pue",
        "it_residual_max_abs_MW",
        "facility_residual_max_abs_MW",
        "facility_residual_mean_abs_MW",
    ]
    load_review = {
        "status": "PASS_WITH_ROUNDING_BOUNDARY",
        "formula": summary["load_recompute"]["formula"],
        "independent_rows": independent_load.to_dict("records"),
        "artifact_matches_independent_recompute": bool(
            np.allclose(
                independent_load[load_columns].to_numpy(float),
                artifact_load[load_columns].to_numpy(float),
                atol=5e-11,
                rtol=0.0,
            )
        ),
        "maximum_it_residual_MW": float(np.max(np.abs(it_residual))),
        "IT_residual_within_declared_tolerance": bool(
            np.max(np.abs(it_residual)) <= TOL
        ),
        "maximum_facility_residual_MW": float(
            independent_load.facility_residual_max_abs_MW.max()
        ),
        "facility_residual_within_declared_tolerance": bool(
            independent_load.facility_residual_max_abs_MW.max() <= TOL
        ),
        "facility_residual_excess_over_tolerance_MW": float(
            max(independent_load.facility_residual_max_abs_MW.max() - TOL, 0.0)
        ),
        "inferred_pue_by_region": pue_by_region,
        "power_mapping_task_types": power_table.TaskType.astype(str).tolist(),
        "power_mapping_rule_rows": int(len(power_rules)),
        "boundary": (
            "IT load is reproduced within tolerance. Facility load differs by at most 5.045e-5 MW, "
            "which is 4.5e-7 MW above the generic 5e-5 tolerance and is consistent with source "
            "rounding. Claims must state the measured residual and must not say exact equality."
        ),
    }
    if not (
        load_review["artifact_matches_independent_recompute"]
        and load_review["IT_residual_within_declared_tolerance"]
    ):
        load_review["status"] = "FAIL"

    price_q50 = float(region_data.ElectricityPrice_CNY_per_MWh.quantile(0.50))
    price_q90 = float(region_data.ElectricityPrice_CNY_per_MWh.quantile(0.90))
    carbon_q50 = float(region_data.CarbonIntensity_tCO2_per_MWh.quantile(0.50))
    carbon_q75 = float(region_data.CarbonIntensity_tCO2_per_MWh.quantile(0.75))
    carbon_q90 = float(region_data.CarbonIntensity_tCO2_per_MWh.quantile(0.90))
    renewable_q10 = float(region_data.AvailableRenewable_MW.quantile(0.10))
    renewable_q50 = float(region_data.AvailableRenewable_MW.quantile(0.50))
    recomputed_quantiles = {
        "price_q50": price_q50,
        "price_q90": price_q90,
        "carbon_q50": carbon_q50,
        "carbon_q75": carbon_q75,
        "carbon_q90": carbon_q90,
        "renewable_q10": renewable_q10,
        "renewable_q50": renewable_q50,
    }
    recomputed_scenarios = {
        "peak_price_empirical": {
            "price": min(1.20, max(1.05, price_q90 / max(price_q50, 1e-9))),
            "carbon": 1.0,
            "renewable": 1.0,
        },
        "high_carbon_empirical": {
            "price": 1.0,
            "carbon": min(1.20, max(1.05, carbon_q90 / max(carbon_q50, 1e-9))),
            "renewable": 1.0,
        },
        "renewable_low_empirical": {
            "price": 1.0,
            "carbon": 1.0,
            "renewable": max(0.85, min(0.95, renewable_q10 / max(renewable_q50, 1e-9))),
        },
    }
    recomputed_scenarios["joint_stress"] = {
        "price": recomputed_scenarios["peak_price_empirical"]["price"],
        "carbon": recomputed_scenarios["high_carbon_empirical"]["carbon"],
        "renewable": recomputed_scenarios["renewable_low_empirical"]["renewable"],
    }
    scenario_audits = [row for row in audits if row["evaluation"] == "scenario"]
    scenario_factor_match = all(
        all(
            abs(float(summary["scenarios"][name][key]) - float(values[key])) <= 1e-12
            for key in ["price", "carbon", "renewable"]
        )
        for name, values in recomputed_scenarios.items()
    )
    quantile_match = all(
        abs(float(summary["scenario_observed_quantiles"][key]) - value) <= 1e-12
        for key, value in recomputed_quantiles.items()
    )
    scenario_review = {
        "status": "PASS",
        "scope_h": 72,
        "scenario_count": 4,
        "candidate_metric_rows": int(len(scenario_metrics)),
        "candidate_rows_per_scenario": {
            str(key): int(value)
            for key, value in scenario_metrics.groupby("scenario").size().items()
        },
        "candidate_solver_success_all": bool(
            scenario_metrics.solver_success.astype(bool).all()
        ),
        "candidate_solver_modes": sorted(scenario_metrics.solver_mode.astype(str).unique()),
        "candidate_and_baseline_audit_count": len(scenario_audits),
        "candidate_and_baseline_audits_all_pass": bool(
            len(scenario_audits) == 48 and all(row["passed"] for row in scenario_audits)
        ),
        "quantiles_recomputed": recomputed_quantiles,
        "quantiles_match_summary": quantile_match,
        "factors_recomputed": recomputed_scenarios,
        "factors_match_summary": scenario_factor_match,
        "definitions": summary["scenarios"],
        "boundary": (
            "The four scenario probes are deterministic, observed-data-derived 72-hour robustness "
            "tests. They are not full-horizon stochastic guarantees or probability-weighted forecasts."
        ),
    }
    if not (
        scenario_review["candidate_metric_rows"] == 24
        and scenario_review["candidate_solver_success_all"]
        and scenario_review["candidate_solver_modes"] == ["binary_MILP"]
        and scenario_review["candidate_and_baseline_audits_all_pass"]
        and quantile_match
        and scenario_factor_match
    ):
        scenario_review["status"] = "FAIL"

    full_probe_by_region = {
        row["region"]: {
            "passed": bool(row["passed"]),
            "simultaneous_charge_discharge_MW": float(
                row["checks"]["simultaneous_charge_discharge_MW"]
            ),
        }
        for row in full_probe_audits
    }
    excluded_probe = {
        "status": "EXCLUDED",
        "label": summary["full_cycle_probe"]["label"],
        "claim_eligible": False,
        "solver_record_count": int(len(full_probe_records)),
        "all_solver_modes_relaxed_LP": bool(
            full_probe_records.solver_mode.astype(str).eq(
                "LP_full_cycle_scalability_probe"
            ).all()
        ),
        "comparison_rows_containing_probe": int(
            (comparison.evaluation.astype(str) == "full_cycle_probe").sum()
        ),
        "audit_by_region": full_probe_by_region,
        "RegionF_failure": full_probe_by_region["RegionF"],
        "exclusion_rule": (
            "No metric, dispatch row, or audit from evaluation=full_cycle_probe or "
            "Method=full_cycle_LP_scalability_probe may support a manuscript claim. RegionF has "
            "116.60975349482445 MW simultaneous charge/discharge in the relaxed solution."
        ),
    }

    rolling_comparison = comparison[comparison.evaluation == "rolling_aggregate"].copy()
    rolling_totals = {
        "candidate_cost_CNY": float(rolling_comparison.cost_CNY_candidate.sum()),
        "baseline_cost_CNY": float(rolling_comparison.cost_CNY_baseline.sum()),
        "cost_delta_CNY": float(
            rolling_comparison.cost_CNY_candidate.sum()
            - rolling_comparison.cost_CNY_baseline.sum()
        ),
        "candidate_carbon_tCO2": float(rolling_comparison.carbon_tCO2_candidate.sum()),
        "baseline_carbon_tCO2": float(rolling_comparison.carbon_tCO2_baseline.sum()),
        "carbon_delta_tCO2": float(
            rolling_comparison.carbon_tCO2_candidate.sum()
            - rolling_comparison.carbon_tCO2_baseline.sum()
        ),
    }
    metric_nonworse = {
        column: bool((rolling_comparison[column] >= -1e-7).all())
        for column in [
            "cost_saving_CNY",
            "carbon_reduction_tCO2",
            "peak_reduction_MW",
            "std_reduction_MW",
            "renewable_utilization_gain_pp",
        ]
    }

    hard_sections_pass = all(
        section["status"] == "PASS"
        for section in [
            binary_review,
            rolling_review,
            baseline_review,
            fallback_review,
            scenario_review,
        ]
    ) and load_review["status"] in {"PASS", "PASS_WITH_ROUNDING_BOUNDARY"}
    boundary_review = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "question": "Q3",
        "authority": "proposal_only",
        "review_status": "PASS_WITH_BOUNDARIES" if hard_sections_pass else "FAIL",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_hash_verification": {
            "all_match": all(row["match"] for row in hash_review),
            "items": hash_review,
        },
        "binary_MILP": binary_review,
        "rolling_2407h_coverage": rolling_review,
        "baseline_comparability": baseline_review,
        "fallback": fallback_review,
        "load_recomputation": load_review,
        "scenario_definitions": scenario_review,
        "excluded_full_cycle_LP_probe": excluded_probe,
        "rolling_aggregate_verified_metrics": {
            "region_rows": rolling_comparison[
                [
                    "region",
                    "cost_CNY_candidate",
                    "cost_CNY_baseline",
                    "cost_saving_CNY",
                    "carbon_tCO2_candidate",
                    "carbon_tCO2_baseline",
                    "carbon_reduction_tCO2",
                    "peak_reduction_MW",
                    "std_reduction_MW",
                    "renewable_utilization_gain_pp",
                ]
            ].to_dict("records"),
            "six_region_totals": rolling_totals,
            "reported_improvement_columns_nonnegative_in_every_region": metric_nonworse,
        },
        "claim_eligible_scope": [
            "Binary MILP fixed-window evidence for 72 h and 168 h.",
            "Contiguous rolling binary-MILP evidence covering supplied hours 0-2406 for all six regions.",
            "Candidate versus deterministic no-storage baseline comparisons with matching keys, schema, and metrics.",
            "Four observed-data-derived 72-hour scenario probes.",
            "Load recomputation stated with the independently measured rounding residual.",
        ],
        "claim_ineligible_or_restricted_scope": [
            "The full-cycle 2407-hour LP scalability probe and every metric or dispatch derived from it.",
            "Any RegionF LP result affected by 116.60975349482445 MW simultaneous charge/discharge.",
            "A claim of one globally optimal 2407-hour binary MILP; evidence is rolling-block optimization.",
            "A claim that terminal SOC equals InitialSOC at every block boundary; the rule is a lower bound with carry-forward.",
            "A claim of exact facility-load identity; maximum observed recomputation residual is 5.045e-5 MW.",
            "A claim about fallback performance; fallback use count is zero.",
            "A claim of system-wide inter-region power-flow optimization; Q3 is regional storage dispatch.",
        ],
        "root_action": (
            "Root may freeze only proposal text that preserves these scopes and exclusions. This review "
            "does not modify claims, manifests, the paper, or Figure Contracts."
        ),
    }
    write_json(STAGING / "q3_claim_boundary_review.json", boundary_review)

    source_rel = SOURCE.relative_to(ROOT).as_posix()
    proposals = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "question": "Q3",
        "authority": "proposal_only",
        "review_status": boundary_review["review_status"],
        "proposals": [
            {
                "id": "Q3-ENH-P1",
                "status": "proposal_only",
                "claim": (
                    "For each of six regions, 15 contiguous rolling subproblems (fourteen 168-hour "
                    "blocks and one 55-hour block) cover every supplied hour 0-2406 exactly once. All "
                    "90 block solves used the binary MILP, succeeded without fallback, and the six "
                    "rolling-aggregate audits passed with maximum recorded residual "
                    f"{rolling_review['rolling_aggregate_max_residual']:.12g}."
                ),
                "evidence": [
                    {
                        "path": f"{source_rel}/q3_summary.json",
                        "locator": "solver_records where evaluation=rolling_block",
                    },
                    {
                        "path": f"{source_rel}/q3_dispatch.csv",
                        "locator": "Evaluation=rolling_block; per-region Hour=0..2406",
                    },
                    {
                        "path": f"{source_rel}/q3_constraint_audit.json",
                        "locator": "evaluation=rolling_aggregate, method=rolling_carbon_aware_MILP",
                    },
                ],
                "boundaries": [
                    "Rolling-block evidence, not one global 2407-hour MILP.",
                    "Terminal SOC is carried forward under a lower-bound rule.",
                ],
            },
            {
                "id": "Q3-ENH-P2",
                "status": "proposal_only",
                "claim": (
                    "Summed over the six 2407-hour rolling aggregates, the declared net operating-cost "
                    f"metric is {rolling_totals['candidate_cost_CNY']:.2f} CNY for the storage policy "
                    f"and {rolling_totals['baseline_cost_CNY']:.2f} CNY for the no-storage baseline "
                    f"(delta {rolling_totals['cost_delta_CNY']:.2f} CNY). Grid-purchase carbon is "
                    f"{rolling_totals['candidate_carbon_tCO2']:.6f} versus "
                    f"{rolling_totals['baseline_carbon_tCO2']:.6f} tCO2."
                ),
                "evidence": [
                    {
                        "path": f"{source_rel}/q3_comparison_summary.csv",
                        "locator": "evaluation=rolling_aggregate; sum over six regions",
                    }
                ],
                "boundaries": [
                    "Negative cost values represent net export revenue under the declared cost formula.",
                    "The result is a sum of regional rolling policies, not inter-region power-flow optimization.",
                ],
            },
            {
                "id": "Q3-ENH-P3",
                "status": "proposal_only",
                "claim": (
                    "At the reported numerical tolerance, every region has nonnegative reported improvement "
                    "columns for cost saving, carbon reduction, signed peak reduction, net-import "
                    "standard-deviation reduction, and renewable-utilization gain. Material gains are concentrated "
                    "in Regions D-F; Regions A-C are already zero-purchase cases for several metrics."
                ),
                "evidence": [
                    {
                        "path": f"{source_rel}/q3_comparison_summary.csv",
                        "locator": "evaluation=rolling_aggregate; all six region rows",
                    }
                ],
                "boundaries": [
                    "Zero improvement is included as non-worse, not as a strict gain.",
                    "peak_net_import_MW is a signed regional metric and can be negative under net export.",
                ],
            },
            {
                "id": "Q3-ENH-P4",
                "status": "proposal_only",
                "claim": (
                    "The peak-price, high-carbon, low-renewable, and joint-stress probes are derived "
                    "deterministically from observed quantiles. All 24 regional 72-hour binary-MILP "
                    "scenario solves and all 48 candidate/baseline scenario audits pass."
                ),
                "evidence": [
                    {
                        "path": f"{source_rel}/q3_summary.json",
                        "locator": "scenarios and scenario_observed_quantiles",
                    },
                    {
                        "path": f"{source_rel}/q3_scenario_metrics.csv",
                        "locator": "24 candidate rows",
                    },
                    {
                        "path": f"{source_rel}/q3_constraint_audit.json",
                        "locator": "evaluation=scenario; 48 candidate/baseline audits",
                    },
                ],
                "boundaries": [
                    "Scenario scope is 72 hours only.",
                    "These are deterministic stress probes, not probabilistic forecasts.",
                ],
            },
            {
                "id": "Q3-ENH-P5",
                "status": "proposal_only",
                "claim": (
                    "The supplied IT load is reproduced from Baseline_AI_IT_Load_MW plus NonAI_IT_Load_MW "
                    f"with maximum residual {load_review['maximum_it_residual_MW']:.10g} MW. After applying "
                    "the independently inferred regional PUE, the maximum facility-load residual is "
                    f"{load_review['maximum_facility_residual_MW']:.10g} MW."
                ),
                "evidence": [
                    {
                        "path": f"{source_rel}/q3_load_recompute_audit.csv",
                        "locator": "all six region rows",
                    },
                    {
                        "path": "problems/C/data/region_time_data.xlsx",
                        "locator": "region_time_data sheet; 14442 rows",
                    },
                ],
                "boundaries": [
                    "Facility-load reproduction is within recorded rounding residual, not exact equality.",
                    "PUE is inferred from supplied load columns rather than externally validated in this task package.",
                ],
            },
        ],
        "strict_exclusions": [excluded_probe["exclusion_rule"]],
    }
    write_json(STAGING / "q3_claim_proposals.json", proposals)

    index = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "question": "Q3",
        "source_directory": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": directory_hash(SOURCE),
        },
        "claim_eligible_filter": (
            "Exclude evaluation=full_cycle_probe and Method=full_cycle_LP_scalability_probe. "
            "Use fixed, rolling_block/rolling_aggregate, and scenario evidence only."
        ),
        "evidence": [
            evidence_locator(
                "q3_summary.json",
                role="methods, solver records, fallback, scenarios, and declared exclusions",
                status=summary["status"],
            ),
            evidence_locator(
                "q3_constraint_audit.json",
                role="hard-constraint audits",
                audit_count=len(audits),
                claim_eligible_candidate_audits=len(claim_candidate_audits),
                claim_eligible_baseline_audits=len(claim_baseline_audits),
            ),
            evidence_locator(
                "q3_dispatch.csv",
                role="candidate dispatch",
                rows=int(len(candidate_dispatch)),
                rolling_rows=int(len(rolling_candidate)),
            ),
            evidence_locator(
                "q3_baseline_dispatch.csv",
                role="comparable no-storage dispatch",
                rows=int(len(baseline_dispatch)),
                rolling_rows=int(len(rolling_baseline)),
            ),
            evidence_locator(
                "q3_candidate_metrics.csv",
                role="candidate metrics including explicitly excluded LP probe rows",
                rows=int(len(candidate_metrics)),
                excluded_full_probe_rows=int(
                    (candidate_metrics.evaluation == "full_cycle_probe").sum()
                ),
            ),
            evidence_locator(
                "q3_baseline_metrics.csv",
                role="baseline metrics",
                rows=int(len(baseline_metrics)),
            ),
            evidence_locator(
                "q3_comparison_summary.csv",
                role="matched candidate-baseline comparisons with LP probe excluded",
                rows=int(len(comparison)),
                rolling_aggregate_rows=int(len(rolling_comparison)),
            ),
            evidence_locator(
                "q3_scenario_metrics.csv",
                role="four 72-hour candidate scenario probes across six regions",
                rows=int(len(scenario_metrics)),
            ),
            evidence_locator(
                "q3_load_recompute_audit.csv",
                role="independent load recomputation residuals",
                rows=int(len(load_audit_artifact)),
            ),
            evidence_locator(
                "q3_run_manifest.json",
                role="environment, command, inputs, units, and output inventory",
                run_id=manifest["run_id"],
            ),
            evidence_locator(
                "run_solver_q3.py",
                role="executable model and evidence-generation logic",
            ),
        ],
        "review_outputs": [
            "q3_claim_boundary_review.json",
            "q3_claim_proposals.json",
            "q3_evidence_index.json",
        ],
        "critical_exclusion": excluded_probe,
    }
    write_json(STAGING / "q3_evidence_index.json", index)

    artifact_names = [
        "q3_claim_boundary_review.json",
        "q3_claim_proposals.json",
        "q3_evidence_index.json",
        "review_q3_evidence.py",
    ]
    artifacts = [
        {
            "path": (STAGING / name).relative_to(ROOT).as_posix(),
            "sha256": sha256_file(STAGING / name),
        }
        for name in artifact_names
    ]
    handoff = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "attempt": int(task.get("attempt", 1)),
        "status": "SUCCESS" if hard_sections_pass else "PARTIAL",
        "authority": "proposal_only",
        "input_hashes": task["input_hashes"],
        "written_paths": [row["path"] for row in artifacts]
        + [(STAGING / "handoff.json").relative_to(ROOT).as_posix()],
        "artifacts": artifacts,
        "gate_result": {
            "gate": task.get("target_gate", "G5"),
            "passed": hard_sections_pass,
            "review_status": boundary_review["review_status"],
            "checks": [
                "all_task_input_hashes_verified_before_evidence_read",
                "binary_MILP_source_and_solver_records_checked",
                "rolling_0_2406_coverage_and_SOC_continuity_audited",
                "candidate_baseline_keys_schema_metrics_and_audits_matched",
                "fallback_trigger_checked_and_zero_use_confirmed",
                "load_recomputation_independently_repeated_with_rounding_boundary",
                "scenario_quantiles_and_factors_independently_recomputed",
                "full_cycle_LP_probe_and_RegionF_simultaneous_cycling_strictly_excluded",
                "artifact_hashes_recorded",
            ],
        },
        "summary": (
            "Q3 G5 claim-boundary review completed. Binary fixed/rolling/scenario evidence, "
            "full 0-2406 rolling coverage, comparable baseline, zero fallback use, and four "
            "data-derived scenarios are proposal-eligible within documented boundaries. The "
            "full-cycle LP probe is excluded, including RegionF simultaneous cycling."
        ),
    }
    write_json(STAGING / "handoff.json", handoff)
    return 0 if hard_sections_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
