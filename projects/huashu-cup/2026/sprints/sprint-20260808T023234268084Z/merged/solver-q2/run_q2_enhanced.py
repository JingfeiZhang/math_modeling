#!/usr/bin/env python
"""Q2 carbon-aware rolling exchange enhancement on real contest data.

The runner starts from the complete FIFO schedule produced by the pinned Q2
pilot, then explores three bounded shadow-price/epsilon policies. Every move
is checked against minute-level GPU, IT-power, facility-power, latency, start,
deadline, and closeout constraints. The previous pilot module supplies only
the pinned data loader, common evaluator, and comparable FIFO implementation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# The pinned predecessor is a read-only task input. Import it without creating
# __pycache__ beside that file, otherwise its declared directory hash changes.
sys.dont_write_bytecode = True


STAGING = Path(__file__).resolve().parent
ROOT = STAGING.parents[3]
SPRINT_ID = "sprint-20260808T023234268084Z"
TASK_ID = "solver-q2"
SEED = 20260801
TASK_PACKAGE_PATH = ROOT / "sprints" / SPRINT_ID / "tasks" / f"{TASK_ID}.json"
BASE_PATH = ROOT / "sprints" / "sprint-20260807T200315378028Z" / "merged" / "solver-q2" / "run_solver_q2.py"
CHUNK_HOURS = 6
MAX_START_OPTIONS = 8
TOL = 1e-7

WINDOWS = (
    {"window_id": "w0000_0024", "start_hour": 0, "arrival_end_hour": 24},
    {"window_id": "w1176_1224", "start_hour": 1176, "arrival_end_hour": 1224},
    {"window_id": "w2328_2400", "start_hour": 2328, "arrival_end_hour": 2400},
)

# These are hypotheses to compare, not fixed model commitments. The selected
# policy is determined only after all windows pass the common hard audit.
POLICIES: tuple[dict[str, Any], ...] = (
    {
        "policy_id": "epsilon_cost_no_carbon_regret",
        "cost_weight": 1.0,
        "carbon_weight": 0.0,
        "wait_weight": 0.015,
        "latency_weight": 0.020,
        "renewable_weight": 0.050,
        "carbon_epsilon_ratio": 0.0,
        "latency_epsilon_ms": 20.0,
    },
    {
        "policy_id": "lagrangian_balanced",
        "cost_weight": 1.0,
        "carbon_weight": 4.0,
        "wait_weight": 0.015,
        "latency_weight": 0.015,
        "renewable_weight": 0.050,
        "carbon_epsilon_ratio": None,
        "latency_epsilon_ms": 35.0,
    },
    {
        "policy_id": "lagrangian_carbon_priority",
        "cost_weight": 1.0,
        "carbon_weight": 12.0,
        "wait_weight": 0.010,
        "latency_weight": 0.010,
        "renewable_weight": 0.050,
        "carbon_epsilon_ratio": None,
        "latency_epsilon_ms": 65.0,
    },
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_hash(path: Path) -> str:
    files = sorted(
        (item for item in path.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(path).as_posix(),
    )
    source = "\n".join(f"{item.relative_to(path).as_posix()}:{sha256(item)}" for item in files)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def verify_input_hashes(task_package: dict[str, Any]) -> None:
    failures: list[str] = []
    for item in task_package["input_hashes"]:
        path = ROOT / str(item["path"])
        observed = directory_hash(path) if item["kind"] == "directory" and path.is_dir() else None
        if item["kind"] != "directory" and path.is_file():
            observed = sha256(path)
        if observed != item["sha256"]:
            failures.append(f"{item['path']} expected={item['sha256']} observed={observed}")
    if failures:
        raise RuntimeError("stale sprint inputs: " + "; ".join(failures))


def load_base_module() -> Any:
    spec = importlib.util.spec_from_file_location("q2_pinned_base", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load pinned Q2 base module: {BASE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def artifact(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}


def policy_score(metrics: dict[str, float], policy: dict[str, Any]) -> float:
    return float(
        policy["cost_weight"] * metrics["cost_CNY"] / 1000.0
        + policy["carbon_weight"] * metrics["carbon_tCO2"]
        + policy["wait_weight"] * metrics["wait_min"]
        + policy["latency_weight"] * metrics["latency_ms"]
        - policy["renewable_weight"] * metrics["renewable_MWh"]
    )


class MinuteResources:
    """Fast minute-level capacity ledger for one representative window."""

    def __init__(self, base: Any, context: dict[str, Any], window: dict[str, int]) -> None:
        self.base = base
        self.context = context
        self.start_m, _arrival_end_m, self.closeout_m = base.window_bounds(window)
        self.length = self.closeout_m - self.start_m
        self.gpu = {region: np.zeros(self.length, dtype=np.int32) for region in context["regions"]}
        self.ai_it = {region: np.zeros(self.length, dtype=float) for region in context["regions"]}
        self.bg_it = {region: np.zeros(self.length, dtype=float) for region in context["regions"]}
        for region in context["regions"]:
            for offset in range(self.length):
                hour = (self.start_m + offset) // 60
                self.bg_it[region][offset] = context["hour_data"][(region, hour)]["nonai"]

    def apply(self, row: dict[str, Any], sign: int) -> None:
        region = str(row["ExecutionRegion"])
        begin = int(row["StartMinute"]) - self.start_m
        end = int(row["EndMinute"]) - self.start_m
        if begin < 0 or end > self.length or end <= begin:
            raise ValueError(f"row outside window ledger: TaskID={row['TaskID']}")
        demand = int(row["GPU_Demand"])
        ai_mw = demand * float(self.context["power"][str(row["TaskType"])])
        self.gpu[region][begin:end] += sign * demand
        self.ai_it[region][begin:end] += sign * ai_mw

    def can_place(self, task: pd.Series, region: str, begin: int, end: int) -> bool:
        i0, i1 = begin - self.start_m, end - self.start_m
        if i0 < 0 or i1 > self.length or i1 <= i0:
            return False
        demand = int(task.GPU_Demand)
        ai_mw = demand * float(self.context["power"][str(task.TaskType)])
        gpu_ok = np.max(self.gpu[region][i0:i1] + demand) <= self.context["gpu_capacity"][region] + TOL
        it_load = self.bg_it[region][i0:i1] + self.ai_it[region][i0:i1] + ai_mw
        it_ok = np.max(it_load) <= self.context["it_capacity"][region] + TOL
        facility_ok = np.max(it_load * self.context["pue"][region]) <= self.context["facility_capacity"][region] + TOL
        return bool(gpu_ok and it_ok and facility_ok)


def candidate_option_pool(
    base: Any,
    task: pd.Series,
    old_row: dict[str, Any],
    context: dict[str, Any],
    window: dict[str, int],
    policy: dict[str, Any],
) -> list[tuple[float, str, int, int, dict[str, float]]]:
    start_m, _arrival_end_m, closeout_m = base.window_bounds(window)
    old_metrics = base.option_metrics(
        task,
        str(old_row["ExecutionRegion"]),
        int(old_row["StartMinute"]),
        int(old_row["EndMinute"]),
        context,
    )
    options: list[tuple[float, str, int, int, dict[str, float]]] = []
    for region in base.candidate_regions(task, context):
        scored_starts: list[tuple[float, int, dict[str, float]]] = []
        for begin in base.event_starts(task, start_m, closeout_m):
            end = begin + int(task.EstimatedDuration_min)
            metrics = base.option_metrics(task, region, begin, end, context)
            if metrics["latency_ms"] > old_metrics["latency_ms"] + policy["latency_epsilon_ms"] + TOL:
                continue
            epsilon = policy["carbon_epsilon_ratio"]
            if epsilon is not None and metrics["carbon_tCO2"] > old_metrics["carbon_tCO2"] * (1.0 + epsilon) + TOL:
                continue
            scored_starts.append((policy_score(metrics, policy), begin, metrics))
        scored_starts.sort(key=lambda item: (item[0], item[1]))
        chosen = scored_starts[:MAX_START_OPTIONS]
        old_begin = int(old_row["StartMinute"])
        if region == str(old_row["ExecutionRegion"]):
            for item in scored_starts:
                if item[1] == old_begin and all(existing[1] != old_begin for existing in chosen):
                    chosen.append(item)
                    break
        for score, begin, metrics in chosen:
            options.append((score, region, begin, begin + int(task.EstimatedDuration_min), metrics))
    return sorted(options, key=lambda item: (item[0], item[4]["latency_ms"], item[2], item[1]))


def rolling_exchange(
    base: Any,
    selected: pd.DataFrame,
    baseline: pd.DataFrame,
    context: dict[str, Any],
    window: dict[str, int],
    policy: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    started = time.perf_counter()
    rows = {int(row["TaskID"]): dict(row) for row in baseline.to_dict("records")}
    resources = MinuteResources(base, context, window)
    for row in rows.values():
        resources.apply(row, +1)

    moved = 0
    moved_region = 0
    moved_time = 0
    objective_gain = 0.0
    evaluated_options = 0
    accepted_ids: list[int] = []
    start_m, arrival_end_m, _closeout_m = base.window_bounds(window)
    priority = {"BatchInference": 0, "AITraining": 1}

    # Six-hour releases preserve a rolling decision structure. Existing FIFO
    # reservations remain in the ledger, so each exchange is feasible against
    # already-arrived and future reserved work, not an isolated batch.
    for chunk_start in range(start_m, arrival_end_m, CHUNK_HOURS * 60):
        chunk_end = min(arrival_end_m, chunk_start + CHUNK_HOURS * 60)
        chunk = selected[
            (selected.TaskType != "RealTimeInference")
            & (selected.ArrivalHour * 60 >= chunk_start)
            & (selected.ArrivalHour * 60 < chunk_end)
        ].copy()
        chunk["_work"] = chunk.GPU_Demand * chunk.EstimatedDuration_min
        chunk["_slack"] = chunk._latest_start - chunk._earliest
        chunk["_priority"] = chunk.TaskType.map(priority)
        chunk = chunk.sort_values(["_work", "_slack", "_priority", "TaskID"], ascending=[False, False, True, True])
        for _, task in chunk.iterrows():
            task_id = int(task.TaskID)
            old = rows[task_id]
            resources.apply(old, -1)
            old_metrics = base.option_metrics(
                task,
                str(old["ExecutionRegion"]),
                int(old["StartMinute"]),
                int(old["EndMinute"]),
                context,
            )
            old_score = policy_score(old_metrics, policy)
            chosen: tuple[float, str, int, int, dict[str, float]] | None = None
            for option in candidate_option_pool(base, task, old, context, window, policy):
                evaluated_options += 1
                score, region, begin, end, metrics = option
                if score >= old_score - 1e-9:
                    continue
                if metrics["cost_CNY"] >= old_metrics["cost_CNY"] - TOL and metrics["carbon_tCO2"] >= old_metrics["carbon_tCO2"] - TOL:
                    continue
                if resources.can_place(task, region, begin, end):
                    chosen = option
                    break
            if chosen is None:
                resources.apply(old, +1)
                continue
            score, region, begin, end, _metrics = chosen
            new_row = dict(old)
            new_row.update({"ExecutionRegion": region, "StartMinute": int(begin), "EndMinute": int(end)})
            rows[task_id] = new_row
            resources.apply(new_row, +1)
            moved += 1
            moved_region += int(region != str(old["ExecutionRegion"]))
            moved_time += int(begin != int(old["StartMinute"]))
            objective_gain += old_score - score
            accepted_ids.append(task_id)

    schedule = pd.DataFrame(rows.values()).sort_values("TaskID").reset_index(drop=True)
    missing = sorted(set(int(v) for v in selected.TaskID) - set(int(v) for v in schedule.TaskID))
    fallback = {
        "name": "CP_SAT_unresolved_task_repair",
        "trigger": "candidate_missing_task_after_exchange",
        "triggered": bool(missing),
        "status": "NOT_RUN",
        "missing_before_repair": len(missing),
        "missing_after_repair": len(missing),
    }
    if missing:
        repair_tasks = selected[selected.TaskID.isin(missing)].copy()
        fixed = schedule.to_dict("records")
        repaired, repair_meta = base.cp_sat_repair(repair_tasks, context, window, fixed)
        fallback.update({"status": repair_meta.get("repair_status", "UNKNOWN"), "repair_meta": repair_meta})
        if not repaired.empty:
            schedule = pd.concat([schedule, repaired], ignore_index=True).sort_values("TaskID")
        remaining = sorted(set(missing) - set(int(v) for v in repaired.TaskID)) if not repaired.empty else missing
        fallback["missing_after_repair"] = len(remaining)

    return schedule, {
        "policy_id": policy["policy_id"],
        "chunk_hours": CHUNK_HOURS,
        "max_start_options_per_region": MAX_START_OPTIONS,
        "moved_task_count": moved,
        "moved_region_count": moved_region,
        "moved_start_count": moved_time,
        "evaluated_feasible_candidates": evaluated_options,
        "shadow_objective_gain": objective_gain,
        "accepted_task_ids": accepted_ids,
        "runtime_seconds": time.perf_counter() - started,
        "fallback": fallback,
    }


def independent_audit(
    base: Any,
    schedule: pd.DataFrame,
    selected: pd.DataFrame,
    context: dict[str, Any],
    window: dict[str, int],
) -> dict[str, Any]:
    expected = set(int(v) for v in selected.TaskID)
    actual_list = [int(v) for v in schedule.TaskID] if "TaskID" in schedule else []
    actual = set(actual_list)
    task_index = selected.set_index("TaskID", drop=False)
    start_m, _arrival_end_m, closeout_m = base.window_bounds(window)
    checks = {
        "task_set_exact": actual == expected,
        "task_id_unique": len(actual_list) == len(actual),
        "duration_identity": True,
        "earliest_start": True,
        "realtime_arrival_start": True,
        "latency_limit": True,
        "SLA_latest_finish": True,
        "closeout_2406": True,
        "GPU_capacity": True,
        "IT_power_capacity": True,
        "facility_power_capacity": True,
        "single_execution_region_no_migration": len(actual_list) == len(actual),
    }
    ledgers = MinuteResources(base, context, window)
    for row in schedule.to_dict("records"):
        task = task_index.loc[int(row["TaskID"])]
        begin, end = int(row["StartMinute"]), int(row["EndMinute"])
        checks["duration_identity"] &= end - begin == int(task.EstimatedDuration_min)
        checks["earliest_start"] &= begin >= max(start_m, int(task._earliest))
        if str(task.TaskType) == "RealTimeInference":
            checks["realtime_arrival_start"] &= begin == int(task.ArrivalHour) * 60
        latency = context["latency"].get((str(task.SourceRegion), str(row["ExecutionRegion"])), math.inf)
        checks["latency_limit"] &= latency <= int(task.MaxLatency_ms)
        checks["SLA_latest_finish"] &= end <= int(task.LatestFinishHour) * 60 and end <= int(task._latest)
        checks["closeout_2406"] &= end <= closeout_m and end <= 2406 * 60
        ledgers.apply(row, +1)

    maxima: dict[str, dict[str, float]] = {}
    for region in context["regions"]:
        gpu = ledgers.gpu[region]
        it = ledgers.bg_it[region] + ledgers.ai_it[region]
        facility = it * context["pue"][region]
        maxima[region] = {
            "GPU": float(np.max(gpu)) if len(gpu) else 0.0,
            "IT_MW": float(np.max(it)) if len(it) else 0.0,
            "facility_MW": float(np.max(facility)) if len(facility) else 0.0,
        }
        checks["GPU_capacity"] &= bool(np.max(gpu) <= context["gpu_capacity"][region] + TOL)
        checks["IT_power_capacity"] &= bool(np.max(it) <= context["it_capacity"][region] + TOL)
        checks["facility_power_capacity"] &= bool(np.max(facility) <= context["facility_capacity"][region] + TOL)
    return {
        "passed": bool(all(checks.values())),
        "checks": {name: bool(value) for name, value in checks.items()},
        "expected_task_count": len(expected),
        "observed_task_count": len(actual_list),
        "capacity_maxima": maxima,
    }


def pareto_flags(frame: pd.DataFrame) -> list[bool]:
    rows = frame.to_dict("records")
    flags: list[bool] = []
    for i, row in enumerate(rows):
        dominated = False
        for j, other in enumerate(rows):
            if i == j:
                continue
            weak = (
                other["cost_CNY"] <= row["cost_CNY"] + TOL
                and other["carbon_tCO2"] <= row["carbon_tCO2"] + TOL
                and other["mean_latency_ms"] <= row["mean_latency_ms"] + TOL
                and other["renewable_utilization_ratio"] >= row["renewable_utilization_ratio"] - TOL
            )
            strict = (
                other["cost_CNY"] < row["cost_CNY"] - TOL
                or other["carbon_tCO2"] < row["carbon_tCO2"] - TOL
                or other["mean_latency_ms"] < row["mean_latency_ms"] - TOL
                or other["renewable_utilization_ratio"] > row["renewable_utilization_ratio"] + TOL
            )
            if weak and strict:
                dominated = True
                break
        flags.append(not dominated)
    return flags


def main() -> int:
    started_at = utcnow()
    run_started = time.perf_counter()
    task_package = json.loads(TASK_PACKAGE_PATH.read_text(encoding="utf-8"))
    verify_input_hashes(task_package)
    base = load_base_module()
    tasks, context = base.load_data()

    baseline_metrics: list[dict[str, Any]] = []
    variant_metrics: list[dict[str, Any]] = []
    schedules: dict[tuple[str, str], pd.DataFrame] = {}
    optimizer_meta: dict[tuple[str, str], dict[str, Any]] = {}
    common_audits: dict[tuple[str, str], dict[str, Any]] = {}
    independent_audits: dict[tuple[str, str], dict[str, Any]] = {}
    prepared: dict[str, tuple[pd.DataFrame, dict[str, Any]]] = {}

    for window in WINDOWS:
        selected, prep = base.prepare_window_tasks(tasks, window)
        prepared[window["window_id"]] = (selected, prep)
        baseline, baseline_meta = base.fifo_baseline(selected, context, window)
        bm, _resources = base.evaluate(baseline, selected, context, window, "FIFO_latency_feasible_local_first")
        bm.update({"optimizer_runtime_seconds": 0.0, "seed": SEED, "unscheduled_count": baseline_meta["unscheduled_count"]})
        ba = independent_audit(base, baseline, selected, context, window)
        bm["independent_audit_passed"] = ba["passed"]
        baseline_metrics.append(bm)
        schedules[(window["window_id"], "baseline")] = baseline
        common_audits[(window["window_id"], "baseline")] = bm
        independent_audits[(window["window_id"], "baseline")] = ba
        for policy in POLICIES:
            candidate, meta = rolling_exchange(base, selected, baseline, context, window, policy)
            method = f"rolling_shadow_price_exchange::{policy['policy_id']}"
            cm, _resources = base.evaluate(candidate, selected, context, window, method)
            ca = independent_audit(base, candidate, selected, context, window)
            cm.update(
                {
                    "policy_id": policy["policy_id"],
                    "optimizer_runtime_seconds": meta["runtime_seconds"],
                    "moved_task_count": meta["moved_task_count"],
                    "moved_region_count": meta["moved_region_count"],
                    "moved_start_count": meta["moved_start_count"],
                    "fallback_triggered": meta["fallback"]["triggered"],
                    "fallback_status": meta["fallback"]["status"],
                    "independent_audit_passed": ca["passed"],
                    "seed": SEED,
                }
            )
            variant_metrics.append(cm)
            schedules[(window["window_id"], policy["policy_id"])] = candidate
            optimizer_meta[(window["window_id"], policy["policy_id"])] = meta
            common_audits[(window["window_id"], policy["policy_id"])] = cm
            independent_audits[(window["window_id"], policy["policy_id"])] = ca

    baseline_frame = pd.DataFrame(baseline_metrics)
    variant_frame = pd.DataFrame(variant_metrics)
    aggregates: list[dict[str, Any]] = []
    base_cost = float(baseline_frame.cost_CNY.sum())
    base_carbon = float(baseline_frame.carbon_tCO2.sum())
    base_tasks = float(baseline_frame.task_count.sum())
    base_latency = float((baseline_frame.mean_latency_ms * baseline_frame.task_count).sum() / base_tasks)
    for policy in POLICIES:
        frame = variant_frame[variant_frame.policy_id == policy["policy_id"]]
        task_total = float(frame.task_count.sum())
        cost = float(frame.cost_CNY.sum())
        carbon = float(frame.carbon_tCO2.sum())
        latency = float((frame.mean_latency_ms * frame.task_count).sum() / task_total)
        renewable = float((frame.renewable_utilization_ratio * frame.task_count).sum() / task_total)
        feasible = bool(frame.audit_passed.all() and frame.independent_audit_passed.all())
        aggregates.append(
            {
                "policy_id": policy["policy_id"],
                "cost_CNY": cost,
                "carbon_tCO2": carbon,
                "mean_latency_ms": latency,
                "renewable_utilization_ratio": renewable,
                "task_completion_rate": float((frame.task_completion_rate * frame.task_count).sum() / task_total),
                "SLA_violation_rate": float((frame.SLA_violation_rate * frame.task_count).sum() / task_total),
                "runtime_seconds": float(frame.optimizer_runtime_seconds.sum()),
                "feasible_all_windows": feasible,
                "cost_change_pct_vs_FIFO": 100.0 * (cost / base_cost - 1.0),
                "carbon_change_pct_vs_FIFO": 100.0 * (carbon / base_carbon - 1.0),
                "latency_change_ms_vs_FIFO": latency - base_latency,
                "selection_utility": 0.45 * cost / base_cost + 0.45 * carbon / base_carbon + 0.10 * latency / 150.0,
            }
        )
    pareto = pd.DataFrame(aggregates)
    pareto["pareto_nondominated"] = pareto_flags(pareto)
    eligible = pareto[pareto.feasible_all_windows & (pareto.task_completion_rate >= 1.0 - TOL) & (pareto.SLA_violation_rate <= TOL)]
    if eligible.empty:
        raise RuntimeError("no policy passed all hard, completion, and SLA checks")
    selected_policy = str(eligible.sort_values(["selection_utility", "runtime_seconds", "policy_id"]).iloc[0].policy_id)
    candidate_frame = variant_frame[variant_frame.policy_id == selected_policy].copy()

    baseline_schedule_frames: list[pd.DataFrame] = []
    candidate_schedule_frames: list[pd.DataFrame] = []
    robustness_rows: list[dict[str, Any]] = []
    audit_windows: list[dict[str, Any]] = []
    for window in WINDOWS:
        window_id = window["window_id"]
        selected, prep = prepared[window_id]
        baseline = schedules[(window_id, "baseline")]
        candidate = schedules[(window_id, selected_policy)]
        baseline_schedule_frames.append(base.flatten_schedule(baseline, window, "FIFO_latency_feasible_local_first", SEED))
        candidate_schedule_frames.append(base.flatten_schedule(candidate, window, f"rolling_shadow_price_exchange::{selected_policy}", SEED))
        bm = baseline_frame[baseline_frame.window_id == window_id].iloc[0]
        cm = candidate_frame[candidate_frame.window_id == window_id].iloc[0]
        robustness_rows.append(
            {
                "window_id": window_id,
                "arrival_start_hour": prep["arrival_start_hour"],
                "arrival_end_hour": prep["arrival_end_hour"],
                "task_count": int(cm.task_count),
                "candidate_cost_CNY": float(cm.cost_CNY),
                "baseline_cost_CNY": float(bm.cost_CNY),
                "cost_change_pct": 100.0 * (float(cm.cost_CNY) / float(bm.cost_CNY) - 1.0),
                "candidate_carbon_tCO2": float(cm.carbon_tCO2),
                "baseline_carbon_tCO2": float(bm.carbon_tCO2),
                "carbon_change_pct": 100.0 * (float(cm.carbon_tCO2) / float(bm.carbon_tCO2) - 1.0),
                "candidate_mean_latency_ms": float(cm.mean_latency_ms),
                "baseline_mean_latency_ms": float(bm.mean_latency_ms),
                "candidate_renewable_utilization_ratio": float(cm.renewable_utilization_ratio),
                "baseline_renewable_utilization_ratio": float(bm.renewable_utilization_ratio),
                "candidate_completion_rate": float(cm.task_completion_rate),
                "candidate_SLA_violation_rate": float(cm.SLA_violation_rate),
                "candidate_runtime_seconds": float(cm.optimizer_runtime_seconds),
                "candidate_common_audit_passed": bool(cm.audit_passed),
                "candidate_independent_audit_passed": bool(cm.independent_audit_passed),
            }
        )
        audit_windows.append(
            {
                "window_id": window_id,
                "baseline": {
                    "common_evaluator": common_audits[(window_id, "baseline")],
                    "independent_evaluator": independent_audits[(window_id, "baseline")],
                },
                "candidate": {
                    "policy_id": selected_policy,
                    "common_evaluator": common_audits[(window_id, selected_policy)],
                    "independent_evaluator": independent_audits[(window_id, selected_policy)],
                    "optimizer": optimizer_meta[(window_id, selected_policy)],
                },
            }
        )

    baseline_schedules_path = STAGING / "q2_baseline_schedules.csv"
    candidate_schedules_path = STAGING / "q2_candidate_schedules.csv"
    baseline_metrics_path = STAGING / "q2_baseline_metrics.csv"
    candidate_metrics_path = STAGING / "q2_candidate_metrics.csv"
    variant_metrics_path = STAGING / "q2_variant_metrics.csv"
    robustness_path = STAGING / "q2_robustness.csv"
    pareto_path = STAGING / "q2_pareto.csv"
    pd.concat(baseline_schedule_frames, ignore_index=True).to_csv(baseline_schedules_path, index=False)
    pd.concat(candidate_schedule_frames, ignore_index=True).to_csv(candidate_schedules_path, index=False)
    baseline_frame.to_csv(baseline_metrics_path, index=False)
    candidate_frame.to_csv(candidate_metrics_path, index=False)
    variant_frame.to_csv(variant_metrics_path, index=False)
    pd.DataFrame(robustness_rows).to_csv(robustness_path, index=False)
    pareto.to_csv(pareto_path, index=False)

    selected_aggregate = pareto[pareto.policy_id == selected_policy].iloc[0].to_dict()
    all_pass = bool(
        baseline_frame.audit_passed.all()
        and baseline_frame.independent_audit_passed.all()
        and candidate_frame.audit_passed.all()
        and candidate_frame.independent_audit_passed.all()
        and (candidate_frame.task_completion_rate >= 1.0 - TOL).all()
        and (candidate_frame.SLA_violation_rate <= TOL).all()
    )
    hard_constraints = [
        "assignment_once",
        "nonpreemption_and_duration_identity",
        "latency_filter",
        "realtime_arrival_start",
        "GPU_capacity",
        "IT_power_capacity",
        "facility_power_capacity",
        "SLA_latest_finish",
        "closeout_end_at_or_before_2406",
        "single_execution_region_no_migration_energy",
    ]
    audit_doc = {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q2",
        "status": "PASS" if all_pass else "FAIL",
        "overall_passed": all_pass,
        "selected_policy": selected_policy,
        "hard_constraints": hard_constraints,
        "metric_definitions": {
            "cost_CNY": "facility energy, including non-AI background, multiplied by hourly regional electricity price",
            "carbon_tCO2": "facility energy, including non-AI background, multiplied by hourly regional carbon intensity",
            "mean_latency_ms": "task-weighted mean source-to-execution network latency",
            "renewable_utilization_ratio": "renewable-first hourly allocation divided by total facility energy",
            "task_completion_rate": "scheduled unique task count divided by selected task count",
            "SLA_violation_rate": "late-finish or real-time start violation count divided by selected task count",
            "runtime_seconds": "wall-clock optimization time excluding workbook load and artifact writing",
        },
        "independent_check_note": "Independent minute ledger and row-identity checks were run separately from the inherited common evaluator.",
        "windows": audit_windows,
        "input_hashes": task_package["input_hashes"],
    }
    write_json(STAGING / "q2_constraint_audit.json", audit_doc)

    claims = {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q2",
        "status": "PROPOSAL_ONLY_ROOT_REVIEW_REQUIRED",
        "selected_policy": selected_policy,
        "proposals": [
            {
                "claim_id": "Q2-PROP-1",
                "claim": "The selected rolling shadow-price exchange produced complete, zero-SLA-violation schedules that passed both common and independent hard audits in all three real-data windows.",
                "evidence": "q2_robustness.csv and q2_constraint_audit.json",
                "boundary": "Only the disjoint 24 h, 48 h, and 72 h representative windows are covered; this is not a full-horizon proof.",
            },
            {
                "claim_id": "Q2-PROP-2",
                "claim": f"Against the same-output FIFO baseline, aggregate cost changed by {selected_aggregate['cost_change_pct_vs_FIFO']:.6f}% and carbon by {selected_aggregate['carbon_change_pct_vs_FIFO']:.6f}% across the evaluated windows.",
                "evidence": "q2_pareto.csv",
                "boundary": "Changes include the same non-AI background in both methods; no global-optimality or causal-generalization claim is made.",
            },
            {
                "claim_id": "Q2-PROP-3",
                "claim": f"The measured task-weighted mean latency tradeoff was {selected_aggregate['latency_change_ms_vs_FIFO']:.6f} ms while every task remained within its MaxLatency_ms constraint.",
                "evidence": "q2_robustness.csv and q2_constraint_audit.json",
                "boundary": "The network model uses the supplied static region-to-region latency matrix and excludes congestion and migration energy, as required by Q2.",
            },
        ],
    }
    write_json(STAGING / "q2_claim_proposals.json", claims)

    summary = {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q2",
        "status": "PASS" if all_pass else "FAIL",
        "scope": "real arrivals in three disjoint representative windows: 0-24 h, 1176-1224 h, and 2328-2400 h; six-hour closeout within the global 2406 h limit",
        "data_counts": {
            "all_workload_rows": int(len(tasks)),
            "evaluated_task_rows": int(baseline_frame.task_count.sum()),
            "regions": len(context["regions"]),
        },
        "exploration": {
            "policies": [dict(policy) for policy in POLICIES],
            "selected_policy": selected_policy,
            "selection_rule": "hard feasibility, completion=1, and SLA=0 first; then minimum declared cost-carbon-latency utility over the evaluated windows",
            "pareto_artifact": artifact(pareto_path),
        },
        "main_method": {
            "name": f"rolling_shadow_price_exchange::{selected_policy}",
            "initial_incumbent": "FIFO_latency_feasible_local_first",
            "decomposition": f"{CHUNK_HOURS}-hour arrival chunks with future FIFO reservations retained",
            "decision_boundary": "real-time tasks are fixed at arrival; only non-real-time tasks are re-timed/reassigned; every accepted move passes a minute-level hard-capacity test",
            "optimality_statement": "bounded deterministic heuristic; no global or full-horizon optimality claim",
        },
        "baseline": {
            "name": "FIFO_latency_feasible_local_first",
            "same_input": True,
            "same_hard_constraints": True,
            "same_output_class": True,
        },
        "fallback": {
            "name": "CP_SAT_unresolved_task_repair",
            "trigger": "candidate_missing_task_after_exchange",
            "count_limit": 1,
            "triggered_any_window": bool(candidate_frame.fallback_triggered.any()),
            "note": "UNKNOWN or empty schedules are never accepted as the main output.",
        },
        "selected_aggregate": selected_aggregate,
        "limitations": [
            "Representative-window evidence is not extrapolated as a guaranteed full 0-2400 h result.",
            "The one-pass rolling exchange can be locally dominated by a joint multi-task exchange.",
            "Hourly prices, carbon intensities, renewable availability, and static network latency are treated as known supplied inputs.",
            "The task specification excludes network traffic and migration energy; neither is added to the objective.",
        ],
        "formal_claim_status": "proposal only; root review and evidence freeze required",
    }
    write_json(STAGING / "q2_enhancement_summary.json", summary)

    primary_artifact_names = [
        "run_q2_enhanced.py",
        "q2_baseline_schedules.csv",
        "q2_candidate_schedules.csv",
        "q2_baseline_metrics.csv",
        "q2_candidate_metrics.csv",
        "q2_variant_metrics.csv",
        "q2_robustness.csv",
        "q2_pareto.csv",
        "q2_constraint_audit.json",
        "q2_claim_proposals.json",
        "q2_enhancement_summary.json",
    ]
    manifest = {
        "schema_version": 1,
        "run_id": "q2-carbon-aware-enhancement-20260808",
        "problem_id": "C",
        "question_id": "Q2",
        "engine": "python",
        "command": [sys.executable, str(STAGING / "run_q2_enhanced.py")],
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "ortools": getattr(__import__("ortools"), "__version__", "unknown"),
            "PYTHONPATH_requirement": "workspace tmp/q2-pilot-deps",
        },
        "random_seed": SEED,
        "inputs": task_package["input_hashes"],
        "code": {
            "runner": artifact(STAGING / "run_q2_enhanced.py"),
            "pinned_base_runner": {"path": BASE_PATH.relative_to(ROOT).as_posix(), "sha256": sha256(BASE_PATH)},
        },
        "methods": {
            "main": f"rolling_shadow_price_exchange::{selected_policy}",
            "baseline": "FIFO_latency_feasible_local_first",
            "fallback": "CP_SAT_unresolved_task_repair",
            "hard_constraints": hard_constraints,
            "policy_parameters": [dict(policy) for policy in POLICIES],
        },
        "metrics": [
            {"name": "cost_CNY", "unit": "CNY"},
            {"name": "carbon_tCO2", "unit": "tCO2"},
            {"name": "mean_latency_ms", "unit": "ms"},
            {"name": "renewable_utilization_ratio", "unit": "ratio"},
            {"name": "task_completion_rate", "unit": "ratio"},
            {"name": "SLA_violation_rate", "unit": "ratio"},
            {"name": "peak_facility_load_MW", "unit": "MW"},
            {"name": "optimizer_runtime_seconds", "unit": "s"},
        ],
        "artifacts": [artifact(STAGING / name) for name in primary_artifact_names],
        "started_at_utc": started_at,
        "duration_seconds": round(time.perf_counter() - run_started, 6),
        "status": "PASS" if all_pass else "FAIL",
    }
    write_json(STAGING / "q2_run_manifest.json", manifest)

    handoff_artifacts = [artifact(STAGING / name) for name in primary_artifact_names]
    handoff_artifacts.append(artifact(STAGING / "q2_run_manifest.json"))
    handoff = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "attempt": int(task_package["attempt"]),
        "status": "SUCCESS" if all_pass else "PARTIAL",
        "input_hashes": task_package["input_hashes"],
        "written_paths": [
            (STAGING / "handoff.json").relative_to(ROOT).as_posix(),
            *[item["path"] for item in handoff_artifacts],
        ],
        "artifacts": handoff_artifacts,
        "gate_result": {
            "gate": task_package["target_gate"],
            "passed": all_pass,
            "checks": [
                "input_hashes_recomputed_before_writes",
                "same_input_same_output_class_FIFO_baseline",
                "three_real_data_robustness_windows",
                "cost_carbon_latency_renewable_completion_SLA_runtime_metrics",
                "common_and_independent_constraint_audits",
                "task_uniqueness_and_duration_identity",
                "realtime_arrival_start",
                "latency_and_SLA",
                "GPU_IT_facility_capacity",
                "closeout_2406",
                "single_explicit_fallback_trigger",
                "bounded_claim_proposals",
                "artifact_hashes_recomputed",
            ],
        },
        "summary": (
            f"Selected {selected_policy} after three-policy real-data comparison; candidate and FIFO both passed all hard audits on 24/48/72-hour windows. No global-optimality or full-horizon claim."
            if all_pass
            else "At least one hard, completion, or SLA audit failed; root review required and no claim may be frozen."
        ),
    }
    write_json(STAGING / "handoff.json", handoff)
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
