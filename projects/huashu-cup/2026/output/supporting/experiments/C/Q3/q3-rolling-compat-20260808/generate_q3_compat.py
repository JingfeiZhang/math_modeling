from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[4]
MAIN_ROOT = (
    PROJECT_ROOT
    / "sprints"
    / "sprint-20260808T023236665505Z"
    / "merged"
    / "solver-q3"
)
REVIEW_ROOT = (
    PROJECT_ROOT
    / "sprints"
    / "sprint-20260808T031200808089Z"
    / "merged"
    / "solver-q3"
)
OUTPUT_ROOT = Path(__file__).resolve().parent

PINNED_HASHES = {
    MAIN_ROOT / "q3_baseline_dispatch.csv": "a427a391f104e45df90f9f108b65e93533ff1af4913dbde37e87120977de85dc",
    MAIN_ROOT / "q3_baseline_metrics.csv": "c1ee560ea9f914ef2b6d5edc3d5329bd7cd2fa8e1eb8643960f2fcfdd12966dd",
    MAIN_ROOT / "q3_candidate_metrics.csv": "2b5ef071cdac2510bed725d12c1128e0d0ca1d7f81476ba4d46d0e889fa7c887",
    MAIN_ROOT / "q3_comparison_summary.csv": "f8af976c7205a93c2b0abbe9caffb2d54ffe2330d2b3bb8506a00b7c77b3e29f",
    MAIN_ROOT / "q3_constraint_audit.json": "2f94f0580363d8f3b8a1ea413b554546da08f9637b740795c82d3c3fe26e0ee1",
    MAIN_ROOT / "q3_dispatch.csv": "d27b9e9f351b2031988080c6f70b3e9881b73a93eb48cfaf59bab058feec374f",
    MAIN_ROOT / "q3_load_recompute_audit.csv": "58e06e32f341de175673fa3a2648638440367a4cc16c95f672eaafebe882e1fb",
    MAIN_ROOT / "q3_run_manifest.json": "d7e9e285c21cbc0c8f2c4d062dbab5d3ef63c53c717a5e1e62cb21561cdbb9ea",
    MAIN_ROOT / "q3_scenario_metrics.csv": "4b67097a73bcc30720301f9fb1068ab354f289b21a9219c7e6edd92227aba3d8",
    MAIN_ROOT / "q3_summary.json": "172a14ab7fdfdbb6acd37b6af3983de01d08163957f1094a20a40d65eadc27dc",
    MAIN_ROOT / "run_solver_q3.py": "81a665d910b5b21bde693873bd0844799acb5398d4684a37f0e6425461d5c1b5",
    REVIEW_ROOT / "q3_claim_boundary_review.json": "5bc6f590e3d0d869032acd26d9e65869adf39580ed3bd49015dcdd7a9778787d",
    REVIEW_ROOT / "q3_claim_proposals.json": "e319d39733239a6ab13e696a18de32a8db2bb4ef029b980211f040a2601fb850",
    REVIEW_ROOT / "q3_evidence_index.json": "3bb3f13559a1d069edfb367a8f23247f0e298d577356754973c1c12ee04fd04c",
    REVIEW_ROOT / "review_q3_evidence.py": "d1d775d96ffcdc58cc0b1da7722645e42ff8549808289b3f9482cf3ceff41b10",
}

REGIONS = [f"Region{letter}" for letter in "ABCDEF"]
EXPECTED_BLOCK_STARTS = [168 * index for index in range(15)]
EXPECTED_BLOCK_HORIZONS = [168] * 14 + [55]
EXCLUDED_REGION_F_SIMULTANEOUS_MW = 116.60975349482445


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def as_bool(value: str) -> bool:
    normalized = value.strip().lower()
    require(normalized in {"true", "false"}, f"invalid Boolean field: {value!r}")
    return normalized == "true"


def max_check_value(audits: list[dict[str, Any]]) -> float:
    values = [
        abs(float(value))
        for audit in audits
        for value in audit.get("checks", {}).values()
        if isinstance(value, (int, float))
    ]
    require(bool(values), "audits do not contain numeric checks")
    return max(values)


def sum_decimal(rows: list[dict[str, str]], field: str) -> float:
    return float(sum((Decimal(row[field]) for row in rows), Decimal(0)))


def verify_pins() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    failures: list[str] = []
    for path, expected in PINNED_HASHES.items():
        if not path.is_file():
            failures.append(f"missing source: {project_path(path)}")
            continue
        observed = sha256(path)
        if observed != expected:
            failures.append(
                f"hash mismatch: {project_path(path)} expected={expected} observed={observed}"
            )
        records.append(
            {
                "path": project_path(path),
                "sha256": observed,
                "pinned_sha256": expected,
            }
        )
    require(not failures, "pinned evidence verification failed:\n" + "\n".join(failures))
    return records


def validate_dispatch_coverage(
    rows: list[dict[str, str]], expected_method: str
) -> dict[str, Any]:
    rolling = [row for row in rows if row["Evaluation"] == "rolling_block"]
    require(
        all(row["Method"] == expected_method for row in rolling),
        f"unexpected rolling dispatch method for {expected_method}",
    )
    by_region: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rolling:
        by_region[row["Region"]].append(row)
    require(sorted(by_region) == REGIONS, "rolling dispatch regions do not match")

    coverage: dict[str, dict[str, Any]] = {}
    for region in REGIONS:
        region_rows = by_region[region]
        hours = [int(row["Hour"]) for row in region_rows]
        starts = sorted({int(row["WindowStart_h"]) for row in region_rows})
        require(len(region_rows) == 2407, f"{region} dispatch row count is not 2407")
        require(hours == list(range(2407)), f"{region} dispatch does not preserve hour order")
        require(len(set(hours)) == 2407, f"{region} dispatch contains duplicate hours")
        require(starts == EXPECTED_BLOCK_STARTS, f"{region} block starts do not match")
        coverage[region] = {
            "row_count": len(region_rows),
            "first_hour": min(hours),
            "last_hour": max(hours),
            "unique_hour_count": len(set(hours)),
            "block_starts": starts,
            "coverage_exact": True,
        }
    return {
        "row_count": len(rolling),
        "region_count": len(by_region),
        "all_regions_exact": all(item["coverage_exact"] for item in coverage.values()),
        "by_region": coverage,
    }


def main() -> None:
    # No output is written until every source hash and structural boundary passes.
    source_records = verify_pins()

    summary = read_json(MAIN_ROOT / "q3_summary.json")
    source_manifest = read_json(MAIN_ROOT / "q3_run_manifest.json")
    constraint_payload = read_json(MAIN_ROOT / "q3_constraint_audit.json")
    boundary_review = read_json(REVIEW_ROOT / "q3_claim_boundary_review.json")
    evidence_index = read_json(REVIEW_ROOT / "q3_evidence_index.json")

    dispatch_rows = read_csv(MAIN_ROOT / "q3_dispatch.csv")
    baseline_dispatch_rows = read_csv(MAIN_ROOT / "q3_baseline_dispatch.csv")
    comparison_rows = read_csv(MAIN_ROOT / "q3_comparison_summary.csv")
    scenario_rows = read_csv(MAIN_ROOT / "q3_scenario_metrics.csv")
    load_rows = read_csv(MAIN_ROOT / "q3_load_recompute_audit.csv")

    require(summary.get("status") == "SUCCESS", "Q3 source summary did not succeed")
    require(summary.get("question") == "Q3", "Q3 source summary question mismatch")
    require(
        boundary_review.get("review_status") == "PASS_WITH_BOUNDARIES",
        "Q3 boundary review did not pass with boundaries",
    )
    require(
        boundary_review.get("authority") == "proposal_only",
        "Q3 boundary review exceeded proposal-only authority",
    )

    solver_records = summary.get("solver_records", [])
    require(isinstance(solver_records, list), "solver_records must be a list")
    rolling_records = [
        record for record in solver_records if record.get("evaluation") == "rolling_block"
    ]
    require(len(rolling_records) == 90, "expected exactly 90 rolling-block solves")
    require(all(record.get("success") is True for record in rolling_records), "rolling solve failed")
    require(
        all(record.get("solver_mode") == "binary_MILP" for record in rolling_records),
        "a rolling solve did not use the binary MILP",
    )
    require(
        all(record.get("used_fallback") is False for record in rolling_records),
        "a rolling solve used fallback",
    )

    block_layout: dict[str, dict[str, Any]] = {}
    for region in REGIONS:
        records = [record for record in rolling_records if record.get("region") == region]
        records.sort(key=lambda record: int(record["window_start_h"]))
        starts = [int(record["window_start_h"]) for record in records]
        horizons = [int(record["horizon_h"]) for record in records]
        require(len(records) == 15, f"{region} does not have 15 rolling solves")
        require(starts == EXPECTED_BLOCK_STARTS, f"{region} solver block starts do not match")
        require(horizons == EXPECTED_BLOCK_HORIZONS, f"{region} solver horizons do not match")
        block_layout[region] = {
            "block_count": len(records),
            "starts_h": starts,
            "horizons_h": horizons,
            "layout_exact": True,
        }

    candidate_coverage = validate_dispatch_coverage(dispatch_rows, "carbon_aware_MILP")
    baseline_coverage = validate_dispatch_coverage(
        baseline_dispatch_rows, "no_storage_renewable_first"
    )
    require(candidate_coverage["row_count"] == 14442, "candidate rolling rows mismatch")
    require(baseline_coverage["row_count"] == 14442, "baseline rolling rows mismatch")

    rolling_comparisons = [
        row for row in comparison_rows if row["evaluation"] == "rolling_aggregate"
    ]
    require(len(rolling_comparisons) == 6, "expected six rolling aggregate comparisons")
    require(
        sorted(row["region"] for row in rolling_comparisons) == REGIONS,
        "rolling comparison regions mismatch",
    )
    require(
        all(row["method_candidate"] == "rolling_carbon_aware_MILP" for row in rolling_comparisons),
        "rolling candidate method mismatch",
    )
    require(
        all(row["method_baseline"] == "no_storage_renewable_first" for row in rolling_comparisons),
        "rolling baseline method mismatch",
    )
    require(
        all(as_bool(row["solver_success_candidate"]) for row in rolling_comparisons),
        "a rolling aggregate candidate record failed",
    )
    require(
        all(as_bool(row["solver_success_baseline"]) for row in rolling_comparisons),
        "a rolling aggregate baseline record failed",
    )

    candidate_cost = sum_decimal(rolling_comparisons, "cost_CNY_candidate")
    baseline_cost = sum_decimal(rolling_comparisons, "cost_CNY_baseline")
    candidate_carbon = sum_decimal(rolling_comparisons, "carbon_tCO2_candidate")
    baseline_carbon = sum_decimal(rolling_comparisons, "carbon_tCO2_baseline")
    cost_delta = candidate_cost - baseline_cost
    carbon_delta = candidate_carbon - baseline_carbon
    improvement_fields = [
        "cost_saving_CNY",
        "carbon_reduction_tCO2",
        "peak_reduction_MW",
        "std_reduction_MW",
        "renewable_utilization_gain_pp",
    ]
    nonnegative_improvements = {
        field: all(Decimal(row[field]) >= Decimal("-1e-9") for row in rolling_comparisons)
        for field in improvement_fields
    }
    require(all(nonnegative_improvements.values()), "a reported improvement column is negative")

    audits = constraint_payload.get("audits", [])
    require(isinstance(audits, list), "constraint audits must be a list")
    require(len(audits) == 270, "total audit count changed")
    audit_passed_count = sum(audit.get("passed") is True for audit in audits)
    require(audit_passed_count == 269, "expected exactly 269 of 270 total audits to pass")

    rolling_aggregate_audits = [
        audit for audit in audits if audit.get("evaluation") == "rolling_aggregate"
    ]
    require(len(rolling_aggregate_audits) == 12, "rolling aggregate audit count changed")
    require(
        all(audit.get("passed") is True for audit in rolling_aggregate_audits),
        "a rolling aggregate audit failed",
    )
    rolling_aggregate_max_residual = max_check_value(rolling_aggregate_audits)

    full_probe_audits = [
        audit
        for audit in audits
        if audit.get("evaluation") == "full_cycle_probe"
        or audit.get("method") == "full_cycle_LP_scalability_probe"
    ]
    require(len(full_probe_audits) == 6, "full-cycle LP audit count changed")
    require(
        sum(audit.get("passed") is True for audit in full_probe_audits) == 5,
        "full-cycle LP audit boundary changed",
    )
    region_f_probe = [audit for audit in full_probe_audits if audit.get("region") == "RegionF"]
    require(len(region_f_probe) == 1, "RegionF full-cycle LP audit is missing or duplicated")
    region_f_simultaneous = float(
        region_f_probe[0]["checks"]["simultaneous_charge_discharge_MW"]
    )
    require(region_f_probe[0].get("passed") is False, "RegionF LP probe unexpectedly passed")
    require(
        region_f_simultaneous == EXCLUDED_REGION_F_SIMULTANEOUS_MW,
        "RegionF simultaneous charge/discharge boundary changed",
    )

    full_probe_index = evidence_index.get("critical_exclusion", {})
    require(full_probe_index.get("claim_eligible") is False, "LP probe became claim eligible")
    require(full_probe_index.get("status") == "EXCLUDED", "LP probe exclusion status changed")
    require(
        float(full_probe_index["RegionF_failure"]["simultaneous_charge_discharge_MW"])
        == region_f_simultaneous,
        "reviewed RegionF LP residual does not match the source audit",
    )

    require(len(scenario_rows) == 24, "expected 24 candidate scenario rows")
    scenario_names = sorted({row["scenario"] for row in scenario_rows})
    require(len(scenario_names) == 4, "expected four deterministic scenarios")
    require(all(as_bool(row["solver_success"]) for row in scenario_rows), "scenario solve failed")
    require(
        all(row["solver_mode"] == "binary_MILP" for row in scenario_rows),
        "a scenario solve did not use binary MILP",
    )
    scenario_counts = Counter(row["scenario"] for row in scenario_rows)
    require(all(count == 6 for count in scenario_counts.values()), "scenario region count changed")
    scenario_audits = [audit for audit in audits if audit.get("evaluation") == "scenario"]
    require(len(scenario_audits) == 48, "scenario audit count changed")
    require(all(audit.get("passed") is True for audit in scenario_audits), "scenario audit failed")

    require(len(load_rows) == 6, "load recomputation region count changed")
    require(sorted(row["Region"] for row in load_rows) == REGIONS, "load regions mismatch")
    require(
        sum(int(Decimal(row["rows"])) for row in load_rows) == 14442,
        "load recomputation row count changed",
    )
    load_review = boundary_review.get("load_recomputation", {})
    require(
        load_review.get("status") == "PASS_WITH_ROUNDING_BOUNDARY",
        "load rounding review status changed",
    )
    maximum_it_residual = float(load_review["maximum_it_residual_MW"])
    maximum_facility_residual = float(load_review["maximum_facility_residual_MW"])
    require(
        maximum_facility_residual == 5.044995509706496e-05,
        "facility recomputation boundary changed",
    )
    require(
        max(Decimal(row["facility_residual_max_abs_MW"]) for row in load_rows)
        == Decimal("0.0000504500"),
        "rounded facility residual artifact changed",
    )

    fallback = boundary_review.get("fallback", {})
    require(fallback.get("summary_used_blocks") == 0, "summary reports fallback use")
    require(fallback.get("solver_record_used_blocks") == 0, "solver reports fallback use")
    require(fallback.get("fallback_dispatch_rows") == 0, "fallback dispatch rows exist")

    reviewed_totals = boundary_review["rolling_aggregate_verified_metrics"][
        "six_region_totals"
    ]
    require(float(reviewed_totals["candidate_cost_CNY"]) == candidate_cost, "candidate cost mismatch")
    require(float(reviewed_totals["baseline_cost_CNY"]) == baseline_cost, "baseline cost mismatch")
    require(float(reviewed_totals["cost_delta_CNY"]) == cost_delta, "cost delta mismatch")
    require(
        float(reviewed_totals["candidate_carbon_tCO2"]) == candidate_carbon,
        "candidate carbon mismatch",
    )
    require(
        float(reviewed_totals["baseline_carbon_tCO2"]) == baseline_carbon,
        "baseline carbon mismatch",
    )
    require(float(reviewed_totals["carbon_delta_tCO2"]) == carbon_delta, "carbon delta mismatch")

    derived = {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q3",
        "evidence_type": "deterministic-derived-compatibility-summary",
        "rolling_binary_milp": {
            "region_count": 6,
            "hours_per_region": 2407,
            "first_hour": 0,
            "last_hour": 2406,
            "blocks_per_region": 15,
            "full_blocks_per_region": 14,
            "full_block_hours": 168,
            "final_block_hours": 55,
            "total_block_solves": len(rolling_records),
            "successful_block_solves": sum(
                record.get("success") is True for record in rolling_records
            ),
            "all_solver_modes_binary": True,
            "maximum_mip_gap": max(float(record["mip_gap"]) for record in rolling_records),
            "fallback_used_blocks": 0,
            "candidate_dispatch_rows": candidate_coverage["row_count"],
            "baseline_dispatch_rows": baseline_coverage["row_count"],
            "candidate_coverage_exact": candidate_coverage["all_regions_exact"],
            "baseline_coverage_exact": baseline_coverage["all_regions_exact"],
            "rolling_aggregate_audit_count": len(rolling_aggregate_audits),
            "rolling_aggregate_audits_passed": sum(
                audit.get("passed") is True for audit in rolling_aggregate_audits
            ),
            "rolling_aggregate_max_recorded_residual": rolling_aggregate_max_residual,
            "block_layout_by_region": block_layout,
        },
        "rolling_aggregate": {
            "region_count": len(rolling_comparisons),
            "candidate_cost_cny": candidate_cost,
            "baseline_cost_cny": baseline_cost,
            "cost_delta_cny": cost_delta,
            "candidate_carbon_tco2": candidate_carbon,
            "baseline_carbon_tco2": baseline_carbon,
            "carbon_delta_tco2": carbon_delta,
            "reported_improvement_columns_nonnegative_in_every_region": nonnegative_improvements,
            "negative_cost_interpretation": "Negative values are net export revenue under the declared operating-cost formula.",
        },
        "deterministic_stress_probes": {
            "scope_hours": 72,
            "scenario_count": len(scenario_names),
            "scenario_names": scenario_names,
            "candidate_solve_count": len(scenario_rows),
            "candidate_solves_successful": sum(as_bool(row["solver_success"]) for row in scenario_rows),
            "candidate_and_baseline_audit_count": len(scenario_audits),
            "candidate_and_baseline_audits_passed": sum(
                audit.get("passed") is True for audit in scenario_audits
            ),
            "probabilistic_interpretation_allowed": False,
        },
        "load_recomputation": {
            "region_count": len(load_rows),
            "row_count": sum(int(Decimal(row["rows"])) for row in load_rows),
            "maximum_it_residual_mw": maximum_it_residual,
            "maximum_facility_residual_mw": maximum_facility_residual,
            "exact_facility_equality": False,
            "interpretation": "The facility-load residual is rounding-scale and must not be described as exact equality.",
        },
        "excluded_full_horizon_lp_probe": {
            "claim_eligible": False,
            "solver_record_count": 6,
            "audit_count": len(full_probe_audits),
            "audits_passed": sum(audit.get("passed") is True for audit in full_probe_audits),
            "region_f_audit_passed": False,
            "region_f_simultaneous_charge_discharge_mw": region_f_simultaneous,
            "exclusion_permanent": True,
        },
        "audit_boundary": {
            "total_audit_count": len(audits),
            "total_audits_passed": audit_passed_count,
            "all_270_audits_passed": False,
        },
        "fallback": {
            "used_blocks": 0,
            "performance_claim_allowed": False,
        },
        "interpretation_limits": [
            "The full supplied horizon is covered by 90 rolling binary-MILP solves, not one global 2407-hour MILP.",
            "The regional rolling policies do not constitute inter-region power-flow optimization.",
            "Terminal SOC is carried forward under a lower-bound rule; equality with initial SOC is not asserted.",
            "The full-horizon LP probe is permanently excluded because RegionF violates the simultaneous charge/discharge audit.",
            "Only 269 of the complete set of 270 audits pass; no all-audits-passed statement is allowed.",
            "No fallback was activated, so fallback effectiveness is not claim eligible.",
        ],
        "sources": source_records,
    }

    summary_path = OUTPUT_ROOT / "q3_derived_summary.json"
    summary_locator = project_path(summary_path)
    proposals = {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q3",
        "status": "root-review-required",
        "authority": "proposal-only",
        "claims": [
            {
                "id": "Q3-ROLLING-BINARY-COVERAGE",
                "status": "verified",
                "statement": "Across six regions, 90 successful rolling binary-MILP solves (14 blocks of 168 hours and one block of 55 hours per region) cover supplied hours 0--2406 exactly once; this is not a global 2407-hour MILP result.",
                "locator": f"{summary_locator}:$.rolling_binary_milp.total_block_solves",
                "unit": "solve",
                "review_boundary": "Rolling-block evidence only; no global-optimality claim.",
            },
            {
                "id": "Q3-ROLLING-COST-DELTA",
                "status": "verified",
                "statement": "Summed over six regional rolling policies, the declared net operating-cost metric differs from the comparable no-storage baseline by the reported amount; negative costs denote net export revenue.",
                "locator": f"{summary_locator}:$.rolling_aggregate.cost_delta_cny",
                "unit": "CNY",
                "review_boundary": "Regional rolling aggregate, not inter-region power-flow optimization.",
            },
            {
                "id": "Q3-ROLLING-CARBON-DELTA",
                "status": "verified",
                "statement": "For the same six regional rolling policies and no-storage baseline, the grid-purchase carbon metric differs by the reported amount.",
                "locator": f"{summary_locator}:$.rolling_aggregate.carbon_delta_tco2",
                "unit": "tCO2",
                "review_boundary": "Uses the declared grid-purchase carbon metric only.",
            },
            {
                "id": "Q3-STRESS-AUDITS-PASSED",
                "status": "verified",
                "statement": "All candidate and comparable-baseline audits for the four observed-data-derived 72-hour stress probes passed.",
                "locator": f"{summary_locator}:$.deterministic_stress_probes.candidate_and_baseline_audits_passed",
                "unit": "audit",
                "review_boundary": "Deterministic 72-hour probes, not probabilistic or full-horizon guarantees.",
            },
            {
                "id": "Q3-FACILITY-LOAD-ROUNDING-RESIDUAL",
                "status": "verified",
                "statement": "Facility load is reproduced from the supplied load components and inferred regional PUE only within the reported maximum rounding-scale residual, not by exact equality.",
                "locator": f"{summary_locator}:$.load_recomputation.maximum_facility_residual_mw",
                "unit": "MW",
                "review_boundary": "The residual must be reported whenever reproduction is claimed.",
            },
            {
                "id": "Q3-EXCLUDED-LP-REGIONF-SIMULTANEOUS",
                "status": "verified",
                "statement": "The full-horizon relaxed LP probe is permanently excluded from claims because its RegionF audit records the reported simultaneous charge/discharge peak.",
                "locator": f"{summary_locator}:$.excluded_full_horizon_lp_probe.region_f_simultaneous_charge_discharge_mw",
                "unit": "MW",
                "review_boundary": "Exclusion evidence only; no LP metric or dispatch row is claim eligible.",
            },
        ],
    }

    summary_path.write_text(
        json.dumps(derived, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    proposals_path = OUTPUT_ROOT / "claim_proposals.json"
    proposals_path.write_text(
        json.dumps(proposals, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    source_artifact_paths = [
        MAIN_ROOT / "q3_summary.json",
        MAIN_ROOT / "q3_constraint_audit.json",
        MAIN_ROOT / "q3_load_recompute_audit.csv",
        MAIN_ROOT / "q3_candidate_metrics.csv",
        MAIN_ROOT / "q3_baseline_metrics.csv",
        MAIN_ROOT / "q3_scenario_metrics.csv",
        MAIN_ROOT / "q3_comparison_summary.csv",
        MAIN_ROOT / "q3_dispatch.csv",
        MAIN_ROOT / "q3_baseline_dispatch.csv",
        REVIEW_ROOT / "q3_claim_boundary_review.json",
        REVIEW_ROOT / "q3_evidence_index.json",
        summary_path,
        proposals_path,
    ]
    model_runner = MAIN_ROOT / "run_solver_q3.py"
    generator = Path(__file__).resolve()
    manifest = {
        "schema_version": 1,
        "run_id": "q3-rolling-compat-20260808",
        "problem_id": "C",
        "question_id": "Q3",
        "engine": "python/scipy.optimize.milp with deterministic evidence derivation",
        "command": [
            "D:/anaconda3/envs/math-modeling/python.exe",
            project_path(model_runner),
        ],
        "environment": {
            "python": source_manifest["python"],
            "platform": source_manifest["platform"],
            "packages": source_manifest["packages"],
        },
        "code": {
            "runner": project_path(model_runner),
            "sha256": sha256(model_runner),
            "compatibility_generator": project_path(generator),
            "compatibility_generator_sha256": sha256(generator),
        },
        "random_seed": int(source_manifest["seed"]),
        "methods": [
            {
                "role": "main",
                "name": "rolling carbon-aware binary MILP",
                "implementation": project_path(model_runner),
                "output_class": "regional hourly storage dispatch and aggregate metrics",
                "claim_eligible_scope": "90 contiguous rolling binary-MILP solves",
            },
            {
                "role": "baseline",
                "name": "deterministic no-storage renewable-first policy",
                "implementation": project_path(model_runner),
                "output_class": "regional hourly dispatch and the same aggregate metrics",
                "comparable_output": True,
            },
        ],
        "fallback": None,
        "inputs": source_records,
        "artifacts": [
            {"path": project_path(path), "sha256": sha256(path)}
            for path in source_artifact_paths
        ],
        "metrics": {
            "rolling_block_solves": {
                "value": len(rolling_records),
                "unit": "solve",
                "definition": "six regions times 15 contiguous rolling blocks",
            },
            "cost_delta": {
                "value": cost_delta,
                "unit": "CNY",
                "definition": "candidate net operating cost minus comparable baseline cost",
            },
            "carbon_delta": {
                "value": carbon_delta,
                "unit": "tCO2",
                "definition": "candidate grid-purchase carbon minus comparable baseline carbon",
            },
            "facility_load_residual": {
                "value": maximum_facility_residual,
                "unit": "MW",
                "definition": "maximum absolute facility-load recomputation residual",
            },
        },
        "metric_definitions": summary["metrics_definition"],
        "units": source_manifest["metric_definitions_and_units"],
        "provenance": {
            "source_run_id": source_manifest["run_id"],
            "source_manifest": project_path(MAIN_ROOT / "q3_run_manifest.json"),
            "source_manifest_sha256": sha256(MAIN_ROOT / "q3_run_manifest.json"),
            "boundary_review": project_path(REVIEW_ROOT / "q3_claim_boundary_review.json"),
            "boundary_review_sha256": sha256(REVIEW_ROOT / "q3_claim_boundary_review.json"),
            "compatibility_outputs": [
                {"path": project_path(summary_path), "sha256": sha256(summary_path)},
                {"path": project_path(proposals_path), "sha256": sha256(proposals_path)},
            ],
        },
        "started_at_utc": source_manifest["started_at_utc"],
        "duration_seconds": float(source_manifest["runtime_s"]),
        "status": "PASS",
    }
    manifest_path = OUTPUT_ROOT / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
