#!/usr/bin/env python
"""Q4 four-cell sequential attribution on the audited 72-hour window.

The Q2 task envelopes are fixed upstream.  Each declared scenario is crossed
with FIFO/candidate task timing and no-storage/integrated-storage dispatch:
A FIFO + no storage, B candidate + no storage, C FIFO + storage, D candidate
+ storage.  Differences are descriptive sequential attribution, never causal
effects or joint full-horizon optimality claims.
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
from typing import Any

import numpy as np
import pandas as pd


STAGING = Path(__file__).resolve().parent
ROOT = STAGING.parents[3]
SPRINT_ID = "sprint-20260808T101814701038Z"
TASK_ID = "solver-q3q4"
WINDOW_ID = "arrival_2328_2399"
WINDOW_START_H = 2328
HORIZON = 72
WINDOW_END_H = WINDOW_START_H + HORIZON
SEED = 20260808
TOL = 5e-5

TASK_PACKAGE = ROOT / "sprints" / SPRINT_ID / "tasks" / "solver-q2.json"
Q2_DIR = ROOT / "sprints" / "sprint-20260808T031146908286Z" / "merged" / "solver-q2"
Q3_DIR = ROOT / "sprints" / "sprint-20260808T023236665505Z" / "merged" / "solver-q3"
Q4_RUNNER = ROOT / "sprints" / "sprint-20260808T031214934335Z" / "merged" / "solver-q4" / "run_solver_q4_final.py"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("q4_final_runner_attribution", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load Q4 runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_inputs(task: dict[str, Any]) -> None:
    failures: list[dict[str, Any]] = []
    for item in task.get("input_hashes", []):
        path = ROOT / str(item["path"])
        observed = sha256_file(path) if path.is_file() else None
        if observed != item.get("sha256"):
            failures.append(
                {"path": item["path"], "expected": item.get("sha256"), "observed": observed}
            )
    if failures:
        raise RuntimeError("stale or missing sprint inputs: " + json.dumps(failures, ensure_ascii=False))


def select_window(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    required = {
        "TaskID",
        "TaskType",
        "ExecutionRegion",
        "ArrivalHour",
        "StartMinute",
        "EndMinute",
        "Duration_min",
        "GPU_Demand",
        "LatestFinishHour",
        "MaxLatency_ms",
        "NetworkLatency_ms",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label} schedule missing columns: {sorted(missing)}")
    selected = frame[frame.ArrivalHour.astype(int).between(WINDOW_START_H, WINDOW_END_H - 1)].copy()
    if len(selected) != 1577:
        raise ValueError(f"{label} window must contain 1577 tasks, observed {len(selected)}")
    if selected.TaskID.duplicated().any():
        raise ValueError(f"{label} window contains duplicate TaskID")
    if (selected.EndMinute.astype(int) <= selected.StartMinute.astype(int)).any():
        raise ValueError(f"{label} window contains non-positive durations")
    if (selected.EndMinute.astype(int) < selected.StartMinute.astype(int) + selected.Duration_min.astype(int)).any():
        raise ValueError(f"{label} window contains duration inconsistency")
    return selected.sort_values("TaskID").reset_index(drop=True)


def service_metrics(schedule: pd.DataFrame) -> dict[str, Any]:
    latest_end = schedule.LatestFinishHour.astype(float).to_numpy() * 60.0
    late = schedule.EndMinute.astype(float).to_numpy() > latest_end + TOL
    realtime_mismatch = schedule.TaskType.astype(str).eq("RealTimeInference").to_numpy() & (
        schedule.StartMinute.astype(int).to_numpy() != schedule.ArrivalHour.astype(int).to_numpy() * 60
    )
    return {
        "task_completion_rate": 1.0,
        "SLA_violation_count": int(np.count_nonzero(late | realtime_mismatch)),
        "SLA_violation_rate": float(np.mean(late | realtime_mismatch)),
        "mean_latency_ms": float(schedule.NetworkLatency_ms.astype(float).mean()),
        "p95_latency_ms": float(np.percentile(schedule.NetworkLatency_ms.astype(float), 95)),
        "task_count": int(len(schedule)),
    }


def audit_digest(audit: dict[str, Any]) -> dict[str, Any]:
    regional = audit.get("regional", {})
    checks: dict[str, float] = {}
    for row in regional.values():
        for key, value in row.get("checks", {}).items():
            checks[key] = max(checks.get(key, 0.0), float(value))
    checks.update({f"system_{key}": float(value) for key, value in audit.get("system", {}).get("checks", {}).items()})
    return {
        "passed": bool(audit.get("passed", False)),
        "regional_passed": bool(all(row.get("passed", False) for row in regional.values())),
        "system_passed": bool(audit.get("system", {}).get("passed", False)),
        "max_check_value": checks,
        "regional_count": int(len(regional)),
        "region_hour_row_count_error": float(audit.get("system", {}).get("checks", {}).get("region_hour_row_count_error", 0.0)),
        "exact_72h_coverage": bool(audit.get("system", {}).get("checks", {}).get("exact_72h_coverage_error", 1.0) <= TOL),
        "observed_peak_net_import_MW": float(audit.get("system", {}).get("observed_peak_net_import_MW", 0.0)),
        "positive_part_peak_MW": float(audit.get("system", {}).get("positive_part_peak_MW", 0.0)),
    }


def dispatch_metrics(
    dispatch: pd.DataFrame,
    cell_id: str,
    scenario: str,
    service: dict[str, Any],
    solver: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any]:
    hourly = dispatch.groupby("Hour", as_index=False).agg(
        system_net_import_MW=("NetGridImport_MW", "sum"),
        system_grid_purchase_MW=("GridPurchase_MW", "sum"),
        system_grid_sell_MW=("GridSell_MW", "sum"),
    )
    signed_peak = float(hourly.system_net_import_MW.max())
    positive_peak = float(max(signed_peak, 0.0))
    available = float(dispatch.AvailableRenewable_MW.sum())
    curtailment = float(dispatch.Curtailment_MW.sum())
    return {
        "scenario": scenario,
        "cell_id": cell_id,
        "task_policy": "candidate" if cell_id in {"B", "D"} else "FIFO",
        "storage_policy": "integrated_storage_MILP" if cell_id in {"C", "D"} else "no_storage_renewable_first",
        "solver_success": bool(solver.get("success", True)),
        "solver_status": str(solver.get("status", "baseline deterministic")),
        "runtime_s": float(solver.get("runtime_s", 0.0)),
        "mip_gap": solver.get("mip_gap"),
        "mip_node_count": solver.get("mip_node_count"),
        "objective_value_normalized": solver.get("objective"),
        "cost_CNY": float(np.dot(dispatch.GridPurchase_MW, dispatch.ElectricityPrice_CNY_per_MWh) - np.dot(dispatch.GridSell_MW, dispatch.SellPrice_CNY_per_MWh)),
        "carbon_tCO2": float(np.dot(dispatch.GridPurchase_MW, dispatch.CarbonIntensity_tCO2_per_MWh)),
        "positive_part_peak_MW": positive_peak,
        "signed_net_import_peak_MW": signed_peak,
        "system_net_import_std_MW": float(hourly.system_net_import_MW.std(ddof=0)),
        "renewable_utilization_ratio": float((available - curtailment) / max(available, 1e-9)),
        "available_renewable_MWh": available,
        "curtailment_MWh": curtailment,
        "grid_purchase_MWh": float(dispatch.GridPurchase_MW.sum()),
        "grid_sell_MWh": float(dispatch.GridSell_MW.sum()),
        "task_completion_rate": float(service["task_completion_rate"]),
        "SLA_violation_count": int(service["SLA_violation_count"]),
        "SLA_violation_rate": float(service["SLA_violation_rate"]),
        "mean_latency_ms": float(service["mean_latency_ms"]),
        "p95_latency_ms": float(service["p95_latency_ms"]),
        "terminal_SOC_min_MWh": float(dispatch.groupby("Region").SOC_MWh.last().min()),
        "terminal_SOC_max_MWh": float(dispatch.groupby("Region").SOC_MWh.last().max()),
        "audit_passed": bool(audit.get("passed", False)),
        "audit": audit_digest(audit),
    }


ATTRIBUTION_METRICS = (
    "cost_CNY",
    "carbon_tCO2",
    "positive_part_peak_MW",
    "signed_net_import_peak_MW",
    "renewable_utilization_ratio",
    "task_completion_rate",
    "SLA_violation_rate",
    "mean_latency_ms",
)


def attribution_rows(metrics: dict[str, dict[str, Any]], scenario: str) -> list[dict[str, Any]]:
    values = {cell: metrics[cell] for cell in ("A", "B", "C", "D")}
    row: dict[str, Any] = {"scenario": scenario}
    for metric in ATTRIBUTION_METRICS:
        row[f"D_minus_B_{metric}"] = float(values["D"][metric] - values["B"][metric])
        row[f"C_minus_A_{metric}"] = float(values["C"][metric] - values["A"][metric])
        row[f"B_minus_A_{metric}"] = float(values["B"][metric] - values["A"][metric])
        row[f"D_minus_C_{metric}"] = float(values["D"][metric] - values["C"][metric])
        row[f"interaction_D_minus_B_minus_C_plus_A_{metric}"] = float(
            values["D"][metric] - values["B"][metric] - values["C"][metric] + values["A"][metric]
        )
    return [row]


def main() -> int:
    started = time.perf_counter()
    STAGING.mkdir(parents=True, exist_ok=True)
    task = json.loads(TASK_PACKAGE.read_text(encoding="utf-8"))
    verify_inputs(task)
    q4 = load_module(Q4_RUNNER)
    candidate_full = pd.read_csv(Q2_DIR / "q2_full_candidate_schedule.csv")
    baseline_full = pd.read_csv(Q2_DIR / "q2_full_baseline_schedule.csv")
    candidate = select_window(candidate_full, "candidate")
    baseline = select_window(baseline_full, "FIFO")
    if set(candidate.TaskID.astype(int)) != set(baseline.TaskID.astype(int)):
        raise ValueError("candidate and FIFO windows do not contain the same TaskID set")

    data = ROOT / "problems" / "C" / "data"
    region_time = pd.read_excel(data / "region_time_data.xlsx", sheet_name="region_time_data")
    gpu = pd.read_excel(data / "GPU_information.xlsx", sheet_name="GPU中心基础情况")
    power = pd.read_excel(data / "power_mapping.xlsx", sheet_name="任务功率映射")
    storage = pd.read_excel(data / "storage_information.xlsx", sheet_name="storage_information")
    pue_map = dict(zip(gpu.Region.astype(str), gpu.PUE.astype(float), strict=True))
    power_map = dict(zip(power.TaskType.astype(str), power.GPU_Power_MW_per_EquivalentGPU.astype(float), strict=True))
    candidate_base, candidate_meta = q4.schedule_to_envelope(candidate, region_time, power_map, pue_map, str(candidate.Method.iloc[0]))
    baseline_base, baseline_meta = q4.schedule_to_envelope(baseline, region_time, power_map, pue_map, str(baseline.Method.iloc[0]))

    q3_summary = json.loads((Q3_DIR / "q3_summary.json").read_text(encoding="utf-8"))
    q3_scenarios = q3_summary["scenarios"]
    scenarios = [{"name": "observed", "price": 1.0, "carbon": 1.0, "renewable": 1.0}]
    scenarios.extend({"name": name, **definition} for name, definition in q3_scenarios.items())
    carbon_q75 = float(q3_summary["scenario_observed_quantiles"]["carbon_q75"])
    service = {"candidate": service_metrics(candidate), "FIFO": service_metrics(baseline)}

    cells = {
        "A": ("FIFO", False, baseline_base),
        "B": ("candidate", False, candidate_base),
        "C": ("FIFO", True, baseline_base),
        "D": ("candidate", True, candidate_base),
    }
    all_rows: list[dict[str, Any]] = []
    scenario_attribution: list[dict[str, Any]] = []
    audit_reports: dict[str, Any] = {}
    cell_reports: dict[str, Any] = {}
    for scenario in scenarios:
        scenario_name = str(scenario["name"])
        scenario_metrics: dict[str, dict[str, Any]] = {}
        scenario_audits: dict[str, Any] = {}
        for cell_id, (policy, with_storage, base_frame) in cells.items():
            frame = q4.apply_scenario(base_frame, scenario, carbon_q75)
            if with_storage:
                dispatch, solver = q4.solve_integrated(frame, storage)
                if not bool(solver.get("success")):
                    raise RuntimeError(f"integrated MILP failed for {scenario_name}/{cell_id}: {solver}")
            else:
                dispatch = q4.baseline_dispatch(frame, storage)
                solver = {
                    "success": True,
                    "status": "deterministic renewable-first no-storage balance",
                    "runtime_s": 0.0,
                    "mip_gap": 0.0,
                    "mip_node_count": 0,
                    "objective": None,
                }
            dispatch["Method"] = f"{cell_id}_{policy}_{'storage' if with_storage else 'no_storage'}"
            audit = q4.audit_dispatch(dispatch, storage, str(dispatch.Method.iloc[0]), None if not with_storage else solver.get("system_peak_variable_MW"))
            service_key = "candidate" if policy == "candidate" else "FIFO"
            metric = dispatch_metrics(dispatch, cell_id, scenario_name, service[service_key], solver, audit)
            scenario_metrics[cell_id] = metric
            scenario_audits[cell_id] = audit_digest(audit)
            all_rows.append(metric)
        scenario_attribution.extend(attribution_rows(scenario_metrics, scenario_name))
        audit_reports[scenario_name] = scenario_audits
        cell_reports[scenario_name] = scenario_metrics

    pd.DataFrame(all_rows).drop(columns=["audit"]).to_csv(STAGING / "q4_attribution.csv", index=False, float_format="%.12f")
    summary = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "question_id": "Q4",
        "status": "SUCCESS" if all(bool(row["audit_passed"]) and bool(row["solver_success"]) for row in all_rows) else "PARTIAL",
        "window": {
            "window_id": WINDOW_ID,
            "absolute_start_hour": WINDOW_START_H,
            "absolute_end_hour_exclusive": WINDOW_END_H,
            "horizon_h": HORIZON,
            "selection_rule": "ArrivalHour in [2328,2399]; exact minute overlap for envelope; closeout after hour 2399 excluded",
            "task_count_per_schedule": int(len(candidate)),
            "same_task_id_set": True,
            "candidate_task_id_sha256": hashlib.sha256(",".join(str(v) for v in sorted(candidate.TaskID.astype(int))).encode("utf-8")).hexdigest(),
            "FIFO_task_id_sha256": hashlib.sha256(",".join(str(v) for v in sorted(baseline.TaskID.astype(int))).encode("utf-8")).hexdigest(),
            "candidate_envelope": candidate_meta,
            "FIFO_envelope": baseline_meta,
        },
        "cells": {
            "A": "FIFO task envelope + no-storage renewable-first balance",
            "B": "candidate task envelope + no-storage renewable-first balance",
            "C": "FIFO task envelope + integrated binary storage MILP",
            "D": "candidate task envelope + integrated binary storage MILP",
        },
        "scenarios": scenarios,
        "cell_metrics": all_rows,
        "sequential_attribution": scenario_attribution,
        "hard_audit_summary": audit_reports,
        "service_metrics": service,
        "units": {
            "cost_CNY": "CNY over bounded 72-hour window",
            "carbon_tCO2": "tCO2 from grid purchase",
            "positive_part_peak_MW": "max(max_hour net grid import, 0)",
            "signed_net_import_peak_MW": "max_hour net grid import; negative means net export",
            "renewable_utilization_ratio": "(available renewable - curtailment) / available renewable",
            "mean_latency_ms": "Q2 task network latency inherited from fixed schedule",
        },
        "interpretation": {
            "primary_claim_eligible": False,
            "attribution_label": "sequential descriptive attribution; interaction is a difference-in-differences diagnostic, not a causal effect",
            "no_joint_optimality": True,
            "no_full_horizon_optimality": True,
            "fixed_upstream_schedules": True,
            "excluded_probe": "RegionF full-horizon relaxed LP simultaneous charge/discharge remains permanently excluded",
            "current_q4_model_retained": True,
            "alternative_replacement_rule": "retain current Q4 bounded integrated MILP unless all four cells use identical inputs, pass hard audits, and improve the declared primary objective vector",
        },
        "input_hashes": task["input_hashes"],
        "code_hash": sha256_file(Path(__file__)),
        "q4_runner_hash": sha256_file(Q4_RUNNER),
        "runtime_s": float(time.perf_counter() - started),
        "generated_at_utc": utcnow(),
        "environment": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__},
    }
    dump_json(STAGING / "q4_attribution_summary.json", summary)
    return 0


if __name__ == "__main__":
    main()
