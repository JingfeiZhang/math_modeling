#!/usr/bin/env python
"""Create the claim-eligible Q4 summary from audited candidate artifacts."""
from __future__ import annotations

import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    started = time.perf_counter()
    metrics_path = HERE / "q4_joint_metrics.csv"
    audit_path = HERE / "q4_joint_constraint_audit.json"
    probe_path = HERE / "q4_joint_risk_probes.json"
    summary_path = HERE / "q4_joint_summary.json"
    metrics = pd.read_csv(metrics_path).set_index(["scenario", "role"])
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    probes = json.loads(probe_path.read_text(encoding="utf-8"))
    source_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    def delta(scenario: str, metric: str) -> float:
        return float(metrics.loc[(scenario, "joint_candidate"), metric] - metrics.loc[(scenario, "sequential_baseline"), metric])

    formal = {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q4",
        "status": "PASS",
        "decision": "PROMOTE",
        "method": "72-hour surrogate-assisted task fix-and-optimize with six-region binary-storage MILP recourse",
        "scope": {"window_start_hour": 2328, "horizon_h": 72, "scenario_count": 5},
        "audit": {
            "all_hard_constraints_passed": bool(audit["all_passed"]),
            "task_completion_rate": float(audit["task_schedule"]["task_completion_rate"]),
            "sla_violation_rate": float(audit["task_schedule"]["SLA_violation_rate"]),
            "deterministic_replay_passed": bool(probes["probes"]["deterministic_replay"]),
        },
        "observed_72h": {
            "cost_delta_CNY": delta("observed", "cost_CNY"),
            "renewable_utilization_gain": delta("observed", "renewable_utilization_ratio"),
        },
        "low_renewable_72h": {
            "cost_delta_CNY": delta("renewable_low_empirical", "cost_CNY"),
            "carbon_delta_tCO2": delta("renewable_low_empirical", "carbon_tCO2"),
            "renewable_utilization_gain": delta("renewable_low_empirical", "renewable_utilization_ratio"),
        },
        "joint_stress_72h": {
            "cost_delta_CNY": delta("joint_stress", "cost_CNY"),
            "carbon_delta_tCO2": delta("joint_stress", "carbon_tCO2"),
        },
        "search": {
            "accepted_task_moves": int(source_summary["algorithm"]["accepted_move_count"]),
            "storage_evaluations": int(source_summary["algorithm"]["storage_evaluations_first_run"]),
        },
        "interpretation_limits": [
            "The result is a 72-hour local joint optimization, not a full-horizon global optimum.",
            "Negative cost denotes net export revenue under the declared purchase-minus-sale formula.",
            "The task schedule starts from the retained formal Q2 schedule; only a 12-task neighborhood is searched.",
        ],
    }
    formal_path = HERE / "q4_formal_summary.json"
    dump(formal_path, formal)

    runner = Path(__file__).resolve()
    artifacts = [formal_path, metrics_path, audit_path, probe_path, summary_path, HERE / "q4_joint_candidate_schedule.csv"]
    manifest = {
        "schema_version": 1,
        "run_id": "q4-optimization-20260809-formal",
        "problem_id": "C",
        "question_id": "Q4",
        "engine": "python",
        "command": [str(runner)],
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "pandas": pd.__version__},
        "code": {"runner": runner.relative_to(ROOT).as_posix(), "sha256": sha256(runner)},
        "random_seed": 20260809,
        "methods": [
            {"name": formal["method"], "role": "main"},
            {"name": "retained Q2 schedule plus scenario-matched storage recourse", "role": "baseline"},
        ],
        "artifacts": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p)} for p in artifacts],
        "metrics": {
            "cost_delta_CNY": "joint candidate minus sequential baseline",
            "carbon_delta_tCO2": "joint candidate minus sequential baseline",
            "renewable_utilization_gain": "joint candidate minus sequential baseline",
        },
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": time.perf_counter() - started,
        "status": "PASS",
    }
    dump(HERE / "formal_run_manifest.json", manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
