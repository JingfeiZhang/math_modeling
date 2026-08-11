from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

import pandas as pd
from ortools.sat.python import cp_model

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / "experiments/C/Q1/q1-direct-20260808/models/scheduling_q1/run_scheduling_q1.py"
SEED = 20260801


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_base():
    spec = importlib.util.spec_from_file_location("q1_schedule_base", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source runner")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.ROOT = ROOT; mod.DATA = ROOT / "problems/C/data"
    return mod


def fixed_neighbour(mod, final_tasks, context, carry, incumbent, count, max_seconds=300.0):
    chosen = final_tasks[~final_tasks.TaskType.eq("RealTimeInference")].assign(_work=lambda x: x.GPU_Demand * x.EstimatedDuration_min).sort_values(["_work", "TaskID"], ascending=[False, True]).head(count)
    chosen_ids = set(chosen.TaskID.astype(int)); inc = incumbent.set_index("TaskID")
    model = cp_model.CpModel(); resources = {r: {"gpu": [], "it": [], "facility": []} for r in context["regions"]}
    for r in context["regions"]:
        idx = context["index"][r]
        for hour in range(mod.Q1_START_H, mod.HORIZON_END_H):
            s, e = hour * 60, (hour + 1) * 60; iv = model.NewIntervalVar(s, 60, e, f"bg_{r}_{hour}"); bg = int(round(context["nonai"][idx, s] * 1000))
            resources[r]["it"].append((iv, bg)); resources[r]["facility"].append((iv, int(round(bg * context["pue"][r]))))
    for _, row in carry.iterrows():
        r = str(row.ExecutionRegion); s, e = max(mod.FINAL_START_M, int(row.StartMinute)), min(mod.FINAL_END_M, int(row.EndMinute))
        if e <= s: continue
        iv = model.NewIntervalVar(s, e - s, e, f"carry_{int(row.TaskID)}"); d = int(row.GPU_Demand); p = context["power"][str(row.TaskType)]
        resources[r]["gpu"].append((iv, d)); resources[r]["it"].append((iv, int(round(d * p * 1000)))); resources[r]["facility"].append((iv, int(round(d * p * context["pue"][r] * 1000))))
    choices = {}; fixed_rows = []
    for _, task in final_tasks.iterrows():
        tid, d, p = int(task.TaskID), int(task.EstimatedDuration_min), context["power"][str(task.TaskType)]
        if tid not in chosen_ids:
            row = inc.loc[tid].to_dict(); row["TaskID"] = tid; fixed_rows.append(row); r, s, e = str(row["ExecutionRegion"]), int(row["StartMinute"]), int(row["EndMinute"]); iv = model.NewIntervalVar(s, e - s, e, f"fixed_{tid}")
            resources[r]["gpu"].append((iv, int(task.GPU_Demand))); resources[r]["it"].append((iv, int(round(int(task.GPU_Demand) * p * 1000)))); resources[r]["facility"].append((iv, int(round(int(task.GPU_Demand) * p * context["pue"][r] * 1000)))); continue
        arrival = max(mod.FINAL_START_M, int(task.ArrivalHour) * 60, int(task.EarliestStartHour) * 60); latest = min(mod.FINAL_END_M, int(task.LatestFinishHour) * 60); opts = []
        inc_row = inc.loc[tid]; inc_start = int(inc_row.StartMinute)
        for r in mod.candidate_regions(task, context):
            if latest - d < arrival: continue
            lo, hi = arrival, latest - d
            if str(task.TaskType) != "RealTimeInference": lo, hi = max(lo, inc_start - 720), min(hi, inc_start + 720)
            if lo > hi: continue
            sv = model.NewIntVar(lo, hi, f"start_{tid}_{r}"); ev = model.NewIntVar(lo + d, hi + d, f"end_{tid}_{r}"); use = model.NewBoolVar(f"use_{tid}_{r}"); model.Add(ev == sv + d)
            iv = model.NewOptionalIntervalVar(sv, d, ev, use, f"job_{tid}_{r}"); dem = int(task.GPU_Demand)
            resources[r]["gpu"].append((iv, dem)); resources[r]["it"].append((iv, int(round(dem * p * 1000)))); resources[r]["facility"].append((iv, int(round(dem * p * context["pue"][r] * 1000)))); opts.append((use, sv, ev, r))
            if r == str(inc_row.ExecutionRegion): model.AddHint(use, 1); model.AddHint(sv, inc_start)
        if not opts: return pd.DataFrame(), {"status": "INFEASIBLE_NO_OPTIONS", "selected_task_count": len(chosen_ids), "selected_task_ids": sorted(chosen_ids)}
        model.AddExactlyOne([o[0] for o in opts]); choices[tid] = opts
    for r in context["regions"]:
        model.AddCumulative([x[0] for x in resources[r]["gpu"]], [x[1] for x in resources[r]["gpu"]], context["gpu_capacity"][r]); model.AddCumulative([x[0] for x in resources[r]["it"]], [x[1] for x in resources[r]["it"]], int(round(context["it_capacity"][r] * 1000))); model.AddCumulative([x[0] for x in resources[r]["facility"]], [x[1] for x in resources[r]["facility"]], int(round(context["facility_capacity"][r] * 1000)))
    objective = []
    task_map = final_tasks.set_index("TaskID", drop=False)
    for tid, opts in choices.items():
        task = task_map.loc[tid]; arrival = int(task.ArrivalHour) * 60
        for use, sv, _ev, r in opts:
            wait = model.NewIntVar(0, mod.FINAL_END_M - mod.FINAL_START_M, f"wait_{tid}_{r}"); model.Add(wait == sv - arrival).OnlyEnforceIf(use); model.Add(wait == 0).OnlyEnforceIf(use.Not()); objective.append(wait * 100 + context["latency"][(str(task.SourceRegion), r)] * use)
    model.Minimize(sum(objective)); solver = cp_model.CpSolver(); solver.parameters.random_seed = SEED; solver.parameters.num_search_workers = 1; solver.parameters.max_time_in_seconds = max_seconds
    started = time.perf_counter(); status = solver.Solve(model); meta = {"status": solver.StatusName(status), "wall_time_seconds": time.perf_counter() - started, "selected_task_count": len(chosen_ids), "selected_task_ids": sorted(chosen_ids), "num_conflicts": solver.NumConflicts(), "num_branches": solver.NumBranches()}
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE): return pd.DataFrame(), meta
    rows = fixed_rows[:]
    for tid, opts in choices.items():
        task = task_map.loc[tid]
        for use, sv, ev, r in opts:
            if solver.Value(use): rows.append(mod.row_for_task(task, r, solver.Value(sv), solver.Value(ev), context, "q1-fix-and-opt")); break
    out = pd.DataFrame(rows).sort_values("TaskID").reset_index(drop=True); obj, bound = float(solver.ObjectiveValue()), float(solver.BestObjectiveBound()); meta.update({"objective": obj, "best_bound": bound, "optimality_gap": (obj - bound) / max(1.0, abs(obj))})
    return out, meta


def main() -> int:
    started = time.perf_counter(); mod = load_base(); tasks, context = mod.load_data(); carry, _, warm = mod.warmup(tasks, context); final_tasks = tasks[tasks.ArrivalHour >= mod.Q1_START_H].copy()
    formal_dir = ROOT / "experiments/C/Q1/q1-direct-20260808/models/scheduling_q1"
    incumbent_all = pd.read_csv(formal_dir / "optimized_schedule.csv"); incumbent = incumbent_all[incumbent_all.SchedulePhase.astype(str).eq("q1-arrival")].copy()
    baseline_all = pd.read_csv(formal_dir / "baseline_schedule.csv"); baseline = baseline_all[baseline_all.SchedulePhase.astype(str).eq("q1-arrival")].copy(); baseline_all.to_csv(OUT / "baseline_schedule.csv", index=False)
    unscheduled = [] if len(baseline) == len(final_tasks) else [{"reason": "formal_baseline_count_mismatch"}]
    candidates = {}; audits = {}
    for count in [12, 32, 64]:
        cand, meta = fixed_neighbour(mod, final_tasks, context, carry, incumbent, count); path = OUT / f"candidate_schedule_{count}.csv"; cand_all = pd.concat([carry, cand], ignore_index=True); cand_all.to_csv(path, index=False); audit = mod.audit_schedule(cand, final_tasks, carry, context) if not cand.empty else {"passed": False, "violations": ["empty_candidate"]}; audit = {k: v for k, v in audit.items() if k != "resource_rows"}
        if not cand.empty: meta["full_schedule_objective"] = int(((cand.StartMinute - cand.ArrivalHour * 60) * 100 + cand.NetworkLatency_ms).sum())
        candidates[str(count)] = meta; audits[str(count)] = audit
    best = min((m for m in candidates.values() if m.get("full_schedule_objective") is not None), key=lambda x: x["full_schedule_objective"], default={})
    dump(OUT / "constraint_audit.json", {"schema_version": 1, "question_id": "Q1", "warmup": {k: v for k, v in warm.items() if k != "history_rows"}, "baseline": {"passed": len(unscheduled) == 0, "unscheduled_count": len(unscheduled)}, "candidates": audits})
    dump(OUT / "schedule_solver_runs.json", candidates)
    formal_objective = int(((incumbent.StartMinute - incumbent.ArrivalHour * 60) * 100 + incumbent.NetworkLatency_ms).sum())
    improved = bool(best.get("full_schedule_objective", formal_objective) <= formal_objective * 0.99)
    dump(OUT / "schedule_summary.json", {"schema_version": 1, "method": "CP-SAT incumbent-hint tight-domain deterministic fix-and-opt", "formal_incumbent_objective": formal_objective, "formal_global_gap": 0.0351506456241033, "baseline_completion_rate": float(len(baseline) / len(final_tasks)), "candidate_completion_rates": {k: float(audits[k].get("scheduled_final_task_count", 0) / len(final_tasks)) for k in audits}, "best_candidate": best, "promotion_gate": {"all_538_complete": all(a.get("passed", False) for a in audits.values()), "local_neighborhood_gap_below_1pct": bool(best.get("optimality_gap", 1.0) < 0.01), "global_gap_below_1pct": False, "full_objective_improves_1pct": improved, "decision": "PROBE_ONLY"}, "scope_note": "Optimality certificates apply only to the released 12/32/64-task neighborhoods; fixed tasks retain the frozen incumbent and no global-gap claim is made.", "runtime_seconds": time.perf_counter() - started})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
