#!/usr/bin/env python
"""Pre-registered Q2 policy sensitivity on the pinned full-horizon solver.

This runner imports the fixed Q2 implementation without changing its source,
reuses one FIFO incumbent, and changes only the declared policy weights. It
does not claim global optimality or causal effects.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pandas as pd


STAGING = Path(__file__).resolve().parent


def find_project_root(start: Path) -> Path:
    """Locate the isolated project root from stable project markers."""
    for candidate in (start, *start.parents):
        if (
            (candidate / "contest.yaml").is_file()
            and (candidate / "config" / "workflow.yaml").is_file()
            and (candidate / "problems").is_dir()
        ):
            return candidate
    raise RuntimeError(f"cannot locate project root from {start}")


ROOT = find_project_root(STAGING)
RUN_ID = "q2-policy-sensitivity-20260808"
PINNED_RUNNER = ROOT / "experiments" / "C" / "Q2" / "q2-direct-20260808" / "models" / "full_horizon" / "run_q2_full_horizon.py"
SEED = 20260801
TOL = 1e-7
POLICY_GRID = [
    ("current", 1.0, 4.0, 0.015, 0.015, 0.05),
    ("cost-lean", 2.0, 2.0, 0.015, 0.015, 0.05),
    ("carbon-lean", 0.5, 8.0, 0.015, 0.015, 0.05),
    ("latency-guarded", 1.0, 4.0, 0.03, 0.03, 0.05),
]
PRIMARY_METRICS = ("cost_CNY", "carbon_tCO2", "mean_latency_ms")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def direct_input_hashes() -> list[dict[str, object]]:
    paths = [
        "problems/C/questions/Q2/question.yaml",
        "contest.yaml",
        "config/workflow.yaml",
        "problems/C/source/problem-C.pdf",
        "problems/C/data/workload_trace.xlsx",
        "problems/C/data/GPU_information.xlsx",
        "problems/C/data/network_latency.xlsx",
        "problems/C/data/region_time_data.xlsx",
        "problems/C/data/power_mapping.xlsx",
    ]
    records = []
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        records.append({"path": relative, "kind": "file", "exists": True, "sha256": sha256(path)})
    records.append({"path": PINNED_RUNNER.relative_to(ROOT).as_posix(), "kind": "file", "exists": True, "sha256": sha256(PINNED_RUNNER)})
    return records


def json_default(value: Any) -> Any:
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=json_default) + "\n",
        encoding="utf-8",
    )


def artifact(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}


def load_pinned_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pinned_q2_full_horizon", PINNED_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import pinned runner: {PINNED_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def policy_dict(module: ModuleType, row: tuple[str, float, float, float, float, float]) -> dict[str, Any]:
    policy_id, cost, carbon, wait, latency, renewable = row
    return {
        "policy_id": policy_id,
        "cost_weight": cost,
        "carbon_weight": carbon,
        "wait_weight": wait,
        "latency_weight": latency,
        "renewable_weight": renewable,
        "latency_epsilon_ms": float(module.LATENCY_EPSILON_MS),
    }


def pct_change(value: float, reference: float) -> float:
    if abs(reference) <= TOL:
        return 0.0
    return 100.0 * (float(value) / float(reference) - 1.0)


def relation_to_current(deltas: dict[str, float]) -> str:
    values = [float(deltas[name]) for name in PRIMARY_METRICS]
    current_dominates = all(value >= -1e-9 for value in values) and any(
        value > 1e-9 for value in values
    )
    candidate_dominates = all(value <= 1e-9 for value in values) and any(
        value < -1e-9 for value in values
    )
    if current_dominates:
        return "DOMINATED_BY_CURRENT"
    if candidate_dominates:
        return "DOMINATES_CURRENT"
    if any(abs(value) > 1e-9 for value in values):
        return "NON_DOMINATED_TRADEOFF"
    return "EQUIVALENT_TO_CURRENT"


def main() -> int:
    started_at = utcnow()
    run_started = time.perf_counter()
    input_hashes = direct_input_hashes()

    np.random.seed(SEED)
    module = load_pinned_module()
    tasks, context = module.load_context()
    baseline, _baseline_ledger, baseline_meta = module.build_fifo_baseline(tasks, context)
    if baseline_meta["unresolved_task_ids"]:
        raise RuntimeError(
            f"FIFO baseline unresolved tasks: {baseline_meta['unresolved_task_ids'][:20]}"
        )
    baseline_audit, _baseline_audit_ledger, _baseline_hourly = module.audit_schedule(
        baseline, tasks, context, module.BASELINE_METHOD
    )
    if not baseline_audit["passed"]:
        raise RuntimeError("FIFO baseline hard audit failed")

    results: list[dict[str, Any]] = []
    current_metrics: dict[str, float] | None = None
    for policy_row in POLICY_GRID:
        policy_id = policy_row[0]
        module.POLICY = policy_dict(module, policy_row)
        variant_started = time.perf_counter()
        candidate, _candidate_ledger, candidate_meta, exchange_log = module.rolling_exchange(
            tasks, baseline, context
        )
        audit, _audit_ledger, _hourly = module.audit_schedule(
            candidate, tasks, context, f"{module.MAIN_METHOD}::{policy_id}"
        )
        metrics = {name: float(audit[name]) for name in PRIMARY_METRICS}
        metrics.update(
            {
                "renewable_utilization_ratio": float(audit["renewable_utilization_ratio"]),
                "mean_wait_hours": float(audit["mean_wait_hours"]),
                "p95_wait_hours": float(audit["p95_wait_hours"]),
                "p95_latency_ms": float(audit["p95_latency_ms"]),
            }
        )
        row: dict[str, Any] = {
            "variant_id": policy_id,
            "policy_id": policy_id,
            "cost_weight": float(policy_row[1]),
            "carbon_weight": float(policy_row[2]),
            "wait_weight": float(policy_row[3]),
            "latency_weight": float(policy_row[4]),
            "renewable_weight": float(policy_row[5]),
            "runtime_seconds": float(time.perf_counter() - variant_started),
            "moved_task_count": int(candidate_meta["moved_task_count"]),
            "moved_region_count": int(candidate_meta["moved_region_count"]),
            "moved_start_count": int(candidate_meta["moved_start_count"]),
            "evaluated_options": int(candidate_meta["evaluated_options"]),
            "accepted_exchange_count": int(len(exchange_log)),
            **metrics,
            "task_completion_rate": float(audit["task_completion_rate"]),
            "SLA_violation_rate": float(audit["SLA_violation_rate"]),
            "hard_audit_passed": bool(audit["passed"]),
            "deterministic_constraints_passed": bool(
                audit["task_completion_rate"] >= 1.0 - TOL
                and audit["SLA_violation_rate"] <= TOL
                and audit["passed"]
            ),
            "cost_change_pct_vs_FIFO": pct_change(metrics["cost_CNY"], baseline_audit["cost_CNY"]),
            "carbon_change_pct_vs_FIFO": pct_change(metrics["carbon_tCO2"], baseline_audit["carbon_tCO2"]),
            "latency_change_pct_vs_FIFO": pct_change(metrics["mean_latency_ms"], baseline_audit["mean_latency_ms"]),
        }
        results.append(row)
        if policy_id == "current":
            current_metrics = metrics

    if current_metrics is None:
        raise RuntimeError("current policy result missing")
    for row in results:
        deltas = {
            name: pct_change(row[name], current_metrics[name])
            for name in PRIMARY_METRICS
        }
        improvements = {name: max(-delta, 0.0) for name, delta in deltas.items()}
        positive_worsening = [delta for delta in deltas.values() if delta > 0.0]
        relation = relation_to_current(deltas)
        max_improvement = max(improvements.values())
        max_worsening = max(positive_worsening, default=0.0)
        valid = bool(
            row["deterministic_constraints_passed"]
            and row["task_completion_rate"] >= 1.0 - TOL
            and row["SLA_violation_rate"] <= TOL
        )
        is_current = row["policy_id"] == "current"
        row.update(
            {
                "cost_change_pct_vs_current": deltas["cost_CNY"],
                "carbon_change_pct_vs_current": deltas["carbon_tCO2"],
                "latency_change_pct_vs_current": deltas["mean_latency_ms"],
                "pareto_relation_vs_current": "REFERENCE_CURRENT" if is_current else relation,
                "best_primary_improvement_pct": 0.0 if is_current else max_improvement,
                "max_primary_worsening_pct": 0.0 if is_current else max_worsening,
                "valid_hard_constraints": valid,
                "eligible_for_root_review": bool(
                    (not is_current)
                    and valid
                    and relation != "DOMINATED_BY_CURRENT"
                    and max_improvement >= 0.25
                    and max_worsening <= 0.25 + 1e-9
                ),
            }
        )

    csv_path = STAGING / "q2_policy_sensitivity.csv"
    summary_path = STAGING / "q2_policy_sensitivity_summary.json"
    frame = pd.DataFrame(results)
    frame.to_csv(csv_path, index=False)
    proposed = [
        row["policy_id"] for row in results if row["eligible_for_root_review"]
    ]
    rejected = [
        {
            "policy_id": row["policy_id"],
            "relation": row["pareto_relation_vs_current"],
            "best_primary_improvement_pct": row["best_primary_improvement_pct"],
            "max_primary_worsening_pct": row["max_primary_worsening_pct"],
            "hard_constraints": row["valid_hard_constraints"],
        }
        for row in results
        if row["policy_id"] != "current" and not row["eligible_for_root_review"]
    ]
    summary = {
        "schema_version": 1,
        "workflow": "direct",
        "run_id": RUN_ID,
        "problem_id": "C",
        "question_id": "Q2",
        "status": "PASS" if all(row["valid_hard_constraints"] for row in results) else "FAIL",
        "evidence_type": "pre-registered-full-horizon-policy-sensitivity",
        "design": {
            "baseline": module.BASELINE_METHOD,
            "main_method": module.MAIN_METHOD,
            "policy_grid": [
                {
                    "policy_id": p[0],
                    "cost_weight": p[1],
                    "carbon_weight": p[2],
                    "wait_weight": p[3],
                    "latency_weight": p[4],
                    "renewable_weight": p[5],
                }
                for p in POLICY_GRID
            ],
            "same_input_same_constraints": True,
            "hard_constraints": [
                "task_assignment_once",
                "nonpreemption_and_duration_identity",
                "release_time_and_realtime_at_arrival",
                "network_latency_and_latest_finish",
                "closeout_end_at_or_before_2406",
                "GPU_capacity",
                "IT_power_capacity",
                "facility_power_capacity",
            ],
            "acceptance_rule": "Every variant must complete all tasks with zero SLA violations and pass hard audits. A non-current policy is eligible for root review only when current does not dominate it, one primary metric improves by at least 0.25%, and no primary metric worsens by more than 0.25%.",
        },
        "baseline_metrics": {
            name: float(baseline_audit[name])
            for name in (
                "cost_CNY",
                "carbon_tCO2",
                "mean_latency_ms",
                "renewable_utilization_ratio",
                "task_completion_rate",
                "SLA_violation_rate",
            )
        },
        "current_policy_id": "current",
        "policy_results": results,
        "decision": {
            "eligible_policy_ids": proposed,
            "recommendation": "PROPOSE_POLICY_FOR_ROOT_REVIEW" if proposed else "RETAIN_CURRENT",
            "formal_model_replacement": False,
        },
        "negative_or_rejected_findings": rejected
        + [
            "The grid is a bounded sensitivity analysis, not a global optimization or causal experiment.",
            "All metrics use the supplied hourly price, carbon, renewable, fixed-load, and static latency inputs.",
            "The current policy remains the reference; any eligible alternative still requires root review and evidence freeze.",
        ],
        "input_hashes_verified": True,
        "run_record": {
            "command": [sys.executable, str(STAGING / "run_q2_policy_sensitivity.py")],
            "environment": {
                "python": sys.version,
                "platform": platform.platform(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "executable": sys.executable,
            },
            "random_seed": SEED,
            "pinned_runner": artifact(PINNED_RUNNER),
            "input_hashes": input_hashes,
            "metric_units": {
                "cost_CNY": "CNY",
                "carbon_tCO2": "tCO2",
                "mean_latency_ms": "ms",
                "renewable_utilization_ratio": "ratio",
                "task_completion_rate": "ratio",
                "SLA_violation_rate": "ratio",
            },
            "started_at_utc": started_at,
            "duration_seconds": round(time.perf_counter() - run_started, 6),
        },
    }
    write_json(summary_path, summary)
    print(json.dumps({"status": summary["status"], "eligible_policy_ids": proposed, "duration_seconds": summary["run_record"]["duration_seconds"]}, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
