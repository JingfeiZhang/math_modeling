from __future__ import annotations

import csv
import hashlib
import json
import platform
import statistics
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SOLVE_SPRINT = PROJECT_ROOT / "sprints" / "sprint-20260807T130848306634Z" / "merged"
FORECAST_ROOT = SOLVE_SPRINT / "forecast-q1"
SCHEDULING_ROOT = SOLVE_SPRINT / "scheduling-q1"
OUTPUT_ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot calculate a quantile from an empty sequence")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def schedule_summary(path: Path) -> dict:
    rows = read_csv(path)
    actual = [row for row in rows if row["SchedulePhase"] != "carry-in"]
    waits = [
        float(row["StartMinute"]) - 60.0 * float(row["ArrivalHour"])
        for row in actual
    ]
    latencies = [float(row["NetworkLatency_ms"]) for row in actual]
    cross_region = [row for row in actual if row["SourceRegion"] != row["ExecutionRegion"]]
    return {
        "row_count_including_carry_in": len(rows),
        "actual_task_count": len(actual),
        "mean_wait_minutes": statistics.fmean(waits),
        "median_wait_minutes": statistics.median(waits),
        "p95_wait_minutes": quantile(waits, 0.95),
        "mean_network_latency_ms": statistics.fmean(latencies),
        "p95_network_latency_ms": quantile(latencies, 0.95),
        "cross_region_task_share": len(cross_region) / len(actual),
        "sla_met_rate": sum(row["SLA_met"].lower() == "true" for row in actual) / len(actual),
    }


def resource_summary(path: Path) -> dict:
    rows = [row for row in read_csv(path) if row["Schedule"] == "optimized"]
    if not rows:
        raise ValueError("optimized resource audit rows are missing")
    return {
        "row_count": len(rows),
        "minimum_gpu_margin": min(float(row["GPU_margin"]) for row in rows),
        "minimum_it_margin_mw": min(float(row["IT_margin_MW"]) for row in rows),
        "minimum_facility_margin_mw": min(float(row["Facility_margin_MW"]) for row in rows),
        "maximum_gpu_utilization_ratio": max(
            float(row["GPU_occupancy"]) / float(row["GPU_capacity"]) for row in rows
        ),
        "maximum_it_utilization_ratio": max(
            float(row["IT_load_MW"]) / float(row["IT_capacity_MW"]) for row in rows
        ),
        "maximum_facility_utilization_ratio": max(
            float(row["Facility_load_MW"]) / float(row["Facility_capacity_MW"]) for row in rows
        ),
    }


def main() -> None:
    forecast_path = FORECAST_ROOT / "metrics_summary.json"
    scheduling_path = SCHEDULING_ROOT / "scheduling_metrics.json"
    carry_path = SCHEDULING_ROOT / "carry_in.json"
    optimized_path = SCHEDULING_ROOT / "optimized_schedule.csv"
    baseline_path = SCHEDULING_ROOT / "baseline_schedule.csv"
    resource_path = SCHEDULING_ROOT / "resource_audit.csv"
    constraint_path = SCHEDULING_ROOT / "constraint_audit.json"
    inputs = [
        forecast_path,
        scheduling_path,
        carry_path,
        optimized_path,
        baseline_path,
        resource_path,
        constraint_path,
    ]
    for path in inputs:
        if not path.is_file():
            raise FileNotFoundError(path)

    forecast = read_json(forecast_path)
    scheduling = read_json(scheduling_path)
    carry = read_json(carry_path)
    constraint = read_json(constraint_path)
    blind = forecast["summaries"]["blind_test"]
    main_wape = float(blind["shared_hgbr_reconciled"]["system_weighted_wape"])
    baseline_wape = float(blind["seasonal_baseline"]["system_weighted_wape"])
    relative_improvement = (baseline_wape - main_wape) / baseline_wape

    optimized = schedule_summary(optimized_path)
    baseline = schedule_summary(baseline_path)
    derived = {
        "schema_version": 1,
        "question_id": "Q1",
        "evidence_type": "deterministic-derived-summary",
        "forecast": {
            "blind_system_weighted_wape_main": main_wape,
            "blind_system_weighted_wape_baseline": baseline_wape,
            "blind_system_weighted_wape_relative_improvement": relative_improvement,
            "blind_empirical_coverage_95": float(
                blind["shared_hgbr_reconciled"]["empirical_coverage_95"]
            ),
        },
        "scheduling": {
            "final_actual_task_count": int(scheduling["final_task_count"]),
            "carry_in_count": int(scheduling["carry_in_count"]),
            "completion_rate": float(scheduling["task_completion_rate"]),
            "solver_status": str(scheduling["main"]["solver"]["status"]),
            "solver_optimality_gap": float(
                scheduling["main"]["solver"]["optimality_gap"]
            ),
            "main": optimized,
            "baseline": baseline,
            "mean_wait_relative_improvement": (
                (baseline["mean_wait_minutes"] - optimized["mean_wait_minutes"])
                / baseline["mean_wait_minutes"]
                if baseline["mean_wait_minutes"] > 0
                else None
            ),
            "resource": resource_summary(resource_path),
            "constraint_audit_passed": bool(constraint["main"]["passed"]),
            "carry_in_record_count": len(carry.get("rows", [])),
        },
        "interpretation_limits": [
            "FEASIBLE solver status does not establish global optimality.",
            "Resource margins describe the nominal optimized schedule only.",
            "Fixed-schedule perturbation failures do not prove re-optimized infeasibility.",
        ],
        "sources": [
            {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256(path),
            }
            for path in inputs
        ],
    }
    summary_path = OUTPUT_ROOT / "q1_derived_summary.json"
    summary_path.write_text(
        json.dumps(derived, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary_locator = summary_path.relative_to(PROJECT_ROOT).as_posix()
    proposals = {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q1",
        "status": "root-review-required",
        "claims": [
            {
                "id": "Q1-FCST-WAPE-IMPROVEMENT",
                "status": "verified",
                "statement": "在2376--2399小时盲测窗口，主模型的系统汇总WAPE相对同口径季节朴素基线下降；该结论不推广为每条底层序列均改善。",
                "locator": f"{summary_locator}:$.forecast.blind_system_weighted_wape_relative_improvement",
                "unit": "ratio",
            },
            {
                "id": "Q1-SCHED-CARRY-IN-COUNT",
                "status": "verified",
                "statement": "历史暖机完整传递到末24小时调度实例的carry-in任务数由派生证据记录，且暖机未静默删除任务。",
                "locator": f"{summary_locator}:$.scheduling.carry_in_count",
                "unit": "task",
            },
            {
                "id": "Q1-SCHED-OPTIMALITY-GAP",
                "status": "verified",
                "statement": "主CP-SAT在固定90秒时限内取得FEASIBLE解时记录的相对最优间隙；该数值不构成全局最优证明。",
                "locator": f"{summary_locator}:$.scheduling.solver_optimality_gap",
                "unit": "ratio",
            },
            {
                "id": "Q1-SCHED-MIN-GPU-MARGIN",
                "status": "verified",
                "statement": "名义主排程独立资源审计中的最小GPU容量裕度；压力扰动下的裕度边界另行报告。",
                "locator": f"{summary_locator}:$.scheduling.resource.minimum_gpu_margin",
                "unit": "GPU",
            },
            {
                "id": "Q1-SCHED-MIN-IT-MARGIN",
                "status": "verified",
                "statement": "名义主排程独立资源审计中的最小IT功率裕度。",
                "locator": f"{summary_locator}:$.scheduling.resource.minimum_it_margin_mw",
                "unit": "MW",
            },
            {
                "id": "Q1-SCHED-MIN-FACILITY-MARGIN",
                "status": "verified",
                "statement": "名义主排程独立资源审计中的最小设施功率裕度。",
                "locator": f"{summary_locator}:$.scheduling.resource.minimum_facility_margin_mw",
                "unit": "MW",
            },
            {
                "id": "Q1-SCHED-MAX-GPU-UTILIZATION",
                "status": "verified",
                "statement": "名义主排程在区域--小时层面的最大GPU利用率由独立资源审计计算。",
                "locator": f"{summary_locator}:$.scheduling.resource.maximum_gpu_utilization_ratio",
                "unit": "ratio",
            },
            {
                "id": "Q1-SCHED-MAIN-MEAN-WAIT",
                "status": "verified",
                "statement": "排除carry-in后，主排程对2376--2399小时实际到达任务的平均等待时间。",
                "locator": f"{summary_locator}:$.scheduling.main.mean_wait_minutes",
                "unit": "min",
            },
            {
                "id": "Q1-SCHED-BASELINE-MEAN-WAIT",
                "status": "verified",
                "statement": "排除carry-in后，同约束本地优先FIFO基线对2376--2399小时实际到达任务的平均等待时间。",
                "locator": f"{summary_locator}:$.scheduling.baseline.mean_wait_minutes",
                "unit": "min",
            },
        ],
    }
    proposals_path = OUTPUT_ROOT / "claim_proposals.json"
    proposals_path.write_text(
        json.dumps(proposals, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": 1,
        "run_id": "q1-derived-20260807",
        "problem_id": "C",
        "question_id": "Q1",
        "engine": "python",
        "command": [
            "conda",
            "run",
            "--no-capture-output",
            "-n",
            "base",
            "python",
            str(Path(__file__).relative_to(PROJECT_ROOT).as_posix()),
        ],
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "random_seed": None,
        "code": {
            "path": Path(__file__).relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256(Path(__file__)),
        },
        "inputs": derived["sources"],
        "outputs": [
            {
                "path": summary_path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256(summary_path),
            },
            {
                "path": proposals_path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256(proposals_path),
            }
        ],
        "metric_definitions": {
            "wape_relative_improvement": "(baseline WAPE - main WAPE) / baseline WAPE",
            "wait_minutes": "StartMinute - 60 * ArrivalHour, excluding carry-in",
            "resource_margin": "capacity - audited peak load in the nominal schedule",
        },
        "units": {
            "wape": "ratio",
            "wait": "min",
            "latency": "ms",
            "gpu_margin": "GPU",
            "power_margin": "MW",
        },
    }
    manifest_path = OUTPUT_ROOT / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
