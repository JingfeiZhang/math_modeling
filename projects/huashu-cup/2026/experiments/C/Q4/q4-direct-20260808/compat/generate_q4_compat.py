from __future__ import annotations

import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
OUTPUT_ROOT = Path(__file__).resolve().parent
FINAL_ROOT = (
    PROJECT_ROOT
    / "sprints"
    / "sprint-20260808T031214934335Z"
    / "merged"
    / "solver-q4"
)
PEAK_ROOT = (
    PROJECT_ROOT
    / "sprints"
    / "sprint-20260808T051118704690Z"
    / "merged"
    / "solver-q4"
)

EXPECTED_INPUTS = {
    FINAL_ROOT / "q4_final_summary.json": "4185d668ab39448c269dd33139e6c895be99de16752aa37c815cff57fb6235e7",
    FINAL_ROOT / "q4_final_constraint_audit.json": "ba148a8192e0dfafef7053c366673cbf7b2e3b26848ea308c0660f80877c790b",
    FINAL_ROOT / "q4_final_run_manifest.json": "f0b8648dc89637ee17a661c54e7466ff2c8f22087b633b38b5ef0c7517f482dd",
    FINAL_ROOT / "run_solver_q4_final.py": "53bbde759fb7b089656a8f14e986d824e7e86332b864232f0131f6de17a8c7f3",
    PEAK_ROOT / "q4_peak_summary.json": "45f18cee089d3f2ae6978940de4de963b09369451ce5365716945fbea66cb274",
    PEAK_ROOT / "q4_peak_constraint_audit.json": "52b190d62209e9373866e33df992046cc4b38f00250283c0e624f4986376ec13",
    PEAK_ROOT / "q4_peak_run_manifest.json": "b280344d00e31ea527f6e109cb914f445b3d11a242abb10841f31ab9d1934406",
    PEAK_ROOT / "q4_peak_tradeoff.csv": "8ed32e82b5bd8ba9c64e3b3d6bfd97bd32e306ce8248ceb1afbce3848b204fcc",
    PEAK_ROOT / "run_q4_peak_budget.py": "fd0afaf0f4471b4e218363621c1601c1d14c1789e281f84d1eb3bc336dd1de1f",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def verify_inputs() -> list[dict[str, str]]:
    records = []
    for path, expected in EXPECTED_INPUTS.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256(path)
        if observed != expected:
            raise RuntimeError(f"stale Q4 input: {relative(path)}")
        records.append({"path": relative(path), "sha256": observed})
    return records


def scenario(summary: dict, name: str) -> dict:
    matches = [row for row in summary["aggregate_comparison"] if row["scenario"] == name]
    if len(matches) != 1:
        raise ValueError(f"expected one scenario row for {name}, found {len(matches)}")
    return matches[0]


def main() -> None:
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    inputs = verify_inputs()
    final = read_json(FINAL_ROOT / "q4_final_summary.json")
    peak = read_json(PEAK_ROOT / "q4_peak_summary.json")

    if final.get("status") != "PASS" or peak.get("status") != "PASS":
        raise RuntimeError("Q4 source summaries are not both PASS")
    if not final["risk_probes"]["all_hard_constraint_audits_passed"]:
        raise RuntimeError("Q4 72-hour hard-constraint audit is not PASS")
    if not peak["hard_audit"]["all_scan_points_passed"]:
        raise RuntimeError("Q4 peak scan hard-constraint audit is not PASS")

    low_renewable = scenario(final, "renewable_low_empirical")
    joint_stress = scenario(final, "joint_stress")
    derived = {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q4",
        "evidence_type": "deterministic-read-only-compatibility-derivation",
        "scope": {
            "sequential_coupling": True,
            "task_storage_joint_optimization": False,
            "final_window_start_hour": 2328,
            "final_window_end_hour": 2399,
            "final_horizon_hours": final["data_counts"]["horizon_h"],
            "regions": final["data_counts"]["regions"],
            "scenarios": final["data_counts"]["scenario_count"],
            "tasks_per_schedule": final["data_counts"]["q2_tasks_per_schedule"],
            "peak_probe_horizon_hours": 24,
        },
        "audit": {
            "final_hard_constraints_passed": final["risk_probes"]["all_hard_constraint_audits_passed"],
            "peak_scan_all_points_passed": peak["hard_audit"]["all_scan_points_passed"],
            "peak_scan_point_count": peak["hard_audit"]["scan_point_count"],
            "q3_relaxed_full_cycle_probe_used_for_claims": final["risk_probes"]["q3_relaxed_full_cycle_probe_used_for_claims"],
        },
        "low_renewable_72h": {
            "candidate_cost_CNY": low_renewable["candidate_cost_CNY"],
            "baseline_cost_CNY": low_renewable["baseline_cost_CNY"],
            "cost_delta_CNY": low_renewable["cost_delta_CNY"],
            "candidate_carbon_tCO2": low_renewable["candidate_carbon_tCO2"],
            "baseline_carbon_tCO2": low_renewable["baseline_carbon_tCO2"],
            "carbon_delta_tCO2": low_renewable["carbon_delta_tCO2"],
            "candidate_signed_max_net_import_MW": low_renewable["candidate_peak_net_import_MW"],
            "baseline_signed_max_net_import_MW": low_renewable["baseline_peak_net_import_MW"],
            "signed_max_net_import_delta_MW": low_renewable["peak_delta_MW"],
            "candidate_renewable_utilization_ratio": low_renewable["candidate_renewable_utilization_ratio"],
            "baseline_renewable_utilization_ratio": low_renewable["baseline_renewable_utilization_ratio"],
            "renewable_utilization_delta": low_renewable["renewable_utilization_delta"],
            "candidate_task_completion_rate": low_renewable["candidate_task_completion_rate"],
            "candidate_SLA_violation_rate": low_renewable["candidate_SLA_violation_rate"],
            "candidate_mean_latency_ms": low_renewable["candidate_mean_latency_ms"],
        },
        "joint_stress_72h": {
            "cost_delta_CNY": joint_stress["cost_delta_CNY"],
            "carbon_delta_tCO2": joint_stress["carbon_delta_tCO2"],
            "signed_max_net_import_delta_MW": joint_stress["peak_delta_MW"],
        },
        "peak_probe_24h": {
            "renewable_multiplier": peak["method"]["renewable_multiplier"],
            "zero_weight_peak_MW": peak["coordination_result"]["zero_price_peak_MW"],
            "selected_peak_weight": peak["coordination_result"]["selected_peak_weight"],
            "selected_peak_MW": peak["coordination_result"]["selected_peak_MW"],
            "peak_reduction_MW": peak["coordination_result"]["peak_reduction_MW"],
            "discrete_marginal_composite_price_per_MW": peak["coordination_result"]["discrete_marginal_composite_price_per_MW"],
        },
        "interpretation_limits": [
            "The 72-hour comparison fixes the upstream Q2 schedules and is a sequential bundle comparison.",
            "The independent 24-hour peak probe is not a full-horizon result.",
            "The discrete marginal composite price is not an LP dual or continuous shadow price.",
            "No task-storage joint or full-horizon global optimality is claimed.",
        ],
        "sources": inputs,
    }
    summary_path = OUTPUT_ROOT / "q4_derived_summary.json"
    write_json(summary_path, derived)

    locator = relative(summary_path)
    proposals = {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q4",
        "status": "root-review-required",
        "claims": [
            {
                "id": "Q4-AUDIT-PASS",
                "status": "verified",
                "statement": "固定 Q2 排程后的 72 小时六区域联合二进制储能 MILP 与独立 24 小时峰值扫描均通过声明范围内的硬约束审计；该结果不代表任务--储能联合全局最优。",
                "locator": f"{locator}:$.audit.final_hard_constraints_passed",
                "unit": "boolean",
            },
            {
                "id": "Q4-LOWREN-COST-DELTA",
                "status": "verified",
                "statement": "在 72 小时低新能源情景中，候选组合相对 FIFO 加无储能基线的运行成本差；该差值同时包含上游任务时序与储能调度效应。",
                "locator": f"{locator}:$.low_renewable_72h.cost_delta_CNY",
                "unit": "CNY",
            },
            {
                "id": "Q4-LOWREN-CARBON-DELTA",
                "status": "verified",
                "statement": "在 72 小时低新能源情景中，候选组合相对基线的购电碳排差；不可拆解为纯储能因果效应。",
                "locator": f"{locator}:$.low_renewable_72h.carbon_delta_tCO2",
                "unit": "tCO2",
            },
            {
                "id": "Q4-PEAK-REDUCTION",
                "status": "verified",
                "statement": "在独立 24 小时低新能源峰值探针中，选定离散峰值权重相对零权重解的系统峰值削减量。",
                "locator": f"{locator}:$.peak_probe_24h.peak_reduction_MW",
                "unit": "MW",
            },
            {
                "id": "Q4-PEAK-SELECTED-WEIGHT",
                "status": "verified",
                "statement": "独立 24 小时峰值扫描按数据派生目标选出的离散复合目标峰值权重；该量不是 LP 对偶变量。",
                "locator": f"{locator}:$.peak_probe_24h.selected_peak_weight",
                "unit": "dimensionless",
            },
            {
                "id": "Q4-PEAK-DISCRETE-MARGINAL",
                "status": "verified",
                "statement": "独立 24 小时扫描给出的离散复合目标边际估计，仅用于比较相邻 MILP 扫描点，不解释为连续影子价格。",
                "locator": f"{locator}:$.peak_probe_24h.discrete_marginal_composite_price_per_MW",
                "unit": "composite-objective/MW",
            },
        ],
    }
    proposals_path = OUTPUT_ROOT / "claim_proposals.json"
    write_json(proposals_path, proposals)

    script_path = Path(__file__).resolve()
    manifest = {
        "schema_version": 1,
        "run_id": "q4-integrated-compat-20260808",
        "problem_id": "C",
        "question_id": "Q4",
        "engine": "python",
        "command": ["python", "-s", relative(script_path)],
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "code": {"runner": relative(script_path), "sha256": sha256(script_path)},
        "random_seed": 20260808,
        "methods": [
            {
                "role": "main",
                "name": "fixed-Q2-schedule plus integrated six-region binary storage MILP",
            },
            {
                "role": "baseline",
                "name": "FIFO schedule plus renewable-first no-storage balance",
            },
        ],
        "inputs": inputs,
        "artifacts": [
            {"path": relative(summary_path), "sha256": sha256(summary_path)},
            {"path": relative(proposals_path), "sha256": sha256(proposals_path)},
        ],
        "metrics": {
            "cost_delta_CNY": "candidate operating cost minus comparable baseline cost",
            "carbon_delta_tCO2": "candidate grid-purchase emissions minus comparable baseline emissions",
            "peak_reduction_MW": "zero-weight system peak minus selected-weight system peak in the 24-hour probe",
        },
        "started_at_utc": started_at,
        "duration_seconds": max(time.perf_counter() - started, 1e-6),
        "status": "PASS",
    }
    write_json(OUTPUT_ROOT / "run_manifest.json", manifest)


if __name__ == "__main__":
    main()
