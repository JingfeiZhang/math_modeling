from __future__ import annotations

"""Deterministic adaptive large-neighbourhood probe for Q2.

The destroy operators are carbon pressure, peak exposure, cross-region
migration, and latency protection.  Every produced schedule is checked by
the pinned minute-level 50,000-task auditor before it is written.
"""

import hashlib
import importlib.util
import json
import math
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SEED = 20260801
METHOD = "adaptive_ALNS_latency_guarded_probe"
MAIN_METHOD = "fixed_weight_bounded_rolling_local_exchange_heuristic"
ITERATIONS = 64
DESTROY_SIZE = 32
RANKING_POOL_SIZE = 256
REACTION = 0.20
COOLING = 0.94
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


OUT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = find_project_root(OUT_DIR)
Q2_ROOT = PROJECT_ROOT / "experiments" / "C" / "Q2" / "q2-direct-20260808"
SOURCE = Q2_ROOT / "models" / "full_horizon" / "run_q2_full_horizon.py"
INCUMBENT_PATH = Q2_ROOT / "models" / "full_horizon" / "q2_full_candidate_schedule.csv"
FIFO_PATH = Q2_ROOT / "models" / "full_horizon" / "q2_full_baseline_schedule.csv"


def load_base():
    spec = importlib.util.spec_from_file_location("q2_full_base", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SOURCE}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = PROJECT_ROOT
    mod.MAIN_METHOD = MAIN_METHOD
    mod.POLICY = {
        "policy_id": "adaptive_alns_latency_guarded",
        "cost_weight": 1.0,
        "carbon_weight": 4.0,
        "wait_weight": 0.03,
        "latency_weight": 0.03,
        "renewable_weight": 0.05,
        "latency_epsilon_ms": 20.0,
    }
    return mod


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def formal_renewable(audit: dict, context: dict) -> float:
    available = float(context["renewable"].sum() / 60.0)
    return float(audit["renewable_used_MWh"] / max(available, 1e-9))


def operator_rankings(mod, tasks: pd.DataFrame, schedule: pd.DataFrame, context: dict, ledger) -> dict[str, list[int]]:
    task_map = tasks.set_index("TaskID")
    flexible = schedule[~schedule.TaskType.astype(str).eq("RealTimeInference")].copy()
    carbon_scores = []
    peak_scores = []
    for row in flexible.itertuples(index=False):
        task = task_map.loc[int(row.TaskID)]
        idx = context["region_index"][str(row.ExecutionRegion)]
        begin, end = int(row.StartMinute), int(row.EndMinute)
        facility_mw = int(row.GPU_Demand) * context["power"][str(row.TaskType)] * context["pue"][str(row.ExecutionRegion)]
        carbon_scores.append((facility_mw * float(context["carbon"][idx, begin:end].mean()) * (end - begin) / 60.0, int(row.TaskID)))
        facility = ledger.facility(str(row.ExecutionRegion))[begin:end]
        peak_scores.append((facility_mw * float(np.percentile(facility, 90)), int(row.TaskID)))
    migrated = flexible.assign(_lat=flexible.NetworkLatency_ms.astype(float), _work=flexible.GPU_Demand.astype(float) * flexible.Duration_min.astype(float)).sort_values(["_lat", "_work", "TaskID"], ascending=[False, False, True])
    latency = flexible.assign(_wait=flexible.StartMinute.astype(float) - flexible.EarliestStartHour.astype(float) * 60.0).sort_values(["NetworkLatency_ms", "_wait", "TaskID"], ascending=[False, False, True])
    return {
        "carbon_pressure_removal": [tid for _score, tid in sorted(carbon_scores, reverse=True)[:RANKING_POOL_SIZE]],
        "peak_time_removal": [tid for _score, tid in sorted(peak_scores, reverse=True)[:RANKING_POOL_SIZE]],
        "cross_region_migration": migrated.head(RANKING_POOL_SIZE).TaskID.astype(int).tolist(),
        "latency_protection_repair": latency.head(RANKING_POOL_SIZE).TaskID.astype(int).tolist(),
    }


def run_alns(mod, tasks: pd.DataFrame, incumbent: pd.DataFrame, context: dict):
    rows = {int(row["TaskID"]): dict(row) for row in incumbent.to_dict("records")}
    ledger = mod.MinuteLedger(context)
    for row in rows.values():
        ledger.apply(row, +1)
    task_map = tasks.set_index("TaskID", drop=False)
    rankings = operator_rankings(mod, tasks, incumbent, context, ledger)
    weights = {name: 1.0 for name in rankings}
    logs: list[dict] = []
    rng = np.random.default_rng(SEED)
    current_proxy = {"score": 0.0, "cost_CNY": 0.0, "carbon_tCO2": 0.0, "latency_ms": 0.0}
    best_proxy = dict(current_proxy)
    best_rows = {tid: dict(row) for tid, row in rows.items()}
    archive: list[dict[str, float]] = [dict(current_proxy, iteration=0)]
    temperature: float | None = None

    for iteration in range(1, ITERATIONS + 1):
        names = sorted(rankings)
        probabilities = np.array([weights[name] for name in names], dtype=float)
        probabilities /= probabilities.sum()
        name = str(rng.choice(names, p=probabilities))
        pool = np.array([tid for tid in rankings[name] if tid in rows], dtype=np.int64)
        take = min(DESTROY_SIZE, len(pool))
        # Rank-biased sampling preserves intensification while allowing diversified
        # task combinations that a deterministic top-k neighbourhood cannot reach.
        rank_probability = 1.0 / np.sqrt(np.arange(1, len(pool) + 1, dtype=float))
        rank_probability /= rank_probability.sum()
        ids = rng.choice(pool, size=take, replace=False, p=rank_probability).astype(int).tolist()
        before = {tid: dict(rows[tid]) for tid in ids}
        for tid in ids:
            ledger.apply(rows[tid], -1)
        feasible = True
        total_delta = 0.0
        component_delta = {"cost_CNY": 0.0, "carbon_tCO2": 0.0, "latency_ms": 0.0}
        repaired: dict[int, dict] = {}
        for tid in sorted(ids, key=lambda x: (-int(task_map.loc[x].GPU_Demand) * int(task_map.loc[x]._duration), x)):
            task = task_map.loc[tid]
            old = before[tid]
            old_metrics = mod.option_metrics(task, str(old["ExecutionRegion"]), int(old["StartMinute"]), ledger, context)
            options = []
            extra_latency = 5.0 if name == "latency_protection_repair" else 20.0
            latency_ceiling = min(float(task.MaxLatency_ms), float(old["NetworkLatency_ms"]) + extra_latency)
            for region in mod.eligible_regions(task, context):
                if context["latency"][(str(task.SourceRegion), region)] > latency_ceiling + mod.TOL:
                    continue
                for begin in mod.candidate_starts(task, region, old, context):
                    if not ledger.can_place(task, region, begin):
                        continue
                    metric = mod.option_metrics(task, region, begin, ledger, context)
                    options.append((metric["score"], metric["latency_ms"], begin, region, metric))
            if not options:
                feasible = False
                break
            best = min(options, key=lambda x: (x[0], x[1], x[2], x[3]))
            row = mod.schedule_row(task, best[3], best[2], METHOD, context, int(task.ArrivalHour) // mod.CHUNK_HOURS)
            repaired[tid] = row
            ledger.apply(row, +1)
            total_delta += float(best[4]["score"] - old_metrics["score"])
            for key in component_delta:
                component_delta[key] += float(best[4][key] - old_metrics[key])
        if temperature is None and feasible:
            temperature = max(abs(total_delta), 1.0)
        accept_probability = 0.0
        if feasible and total_delta >= -1e-9:
            accept_probability = math.exp(-max(total_delta, 0.0) / max(float(temperature), 1e-9))
        accepted = bool(feasible and (total_delta < -1e-9 or rng.random() < accept_probability))
        if accepted:
            rows.update(repaired)
            for key in current_proxy:
                current_proxy[key] += total_delta if key == "score" else component_delta[key]
            improved_best = current_proxy["score"] < best_proxy["score"] - 1e-9
            if improved_best:
                best_proxy = dict(current_proxy)
                best_rows = {tid: dict(row) for tid, row in rows.items()}
            reward = 5.0 if improved_best else (2.0 if total_delta < -1e-9 else 0.5)
        else:
            for row in repaired.values():
                ledger.apply(row, -1)
            for tid, row in before.items():
                ledger.apply(row, +1)
            reward = 0.2
        weights[name] = (1.0 - REACTION) * weights[name] + REACTION * reward
        temperature = max(float(temperature) * COOLING, 1e-6)
        if accepted:
            point = dict(current_proxy, iteration=iteration)
            dominated = any(
                old["cost_CNY"] <= point["cost_CNY"]
                and old["carbon_tCO2"] <= point["carbon_tCO2"]
                and old["latency_ms"] <= point["latency_ms"]
                and (old["cost_CNY"] < point["cost_CNY"] or old["carbon_tCO2"] < point["carbon_tCO2"] or old["latency_ms"] < point["latency_ms"])
                for old in archive
            )
            if not dominated:
                archive = [old for old in archive if not (point["cost_CNY"] <= old["cost_CNY"] and point["carbon_tCO2"] <= old["carbon_tCO2"] and point["latency_ms"] <= old["latency_ms"])]
                archive.append(point)
        logs.append({
            "iteration": iteration, "operator": name, "destroy_count": len(ids),
            "feasible_repair": feasible, "accepted": accepted,
            "accept_probability": accept_probability, "local_score_delta": total_delta,
            "current_proxy_score": current_proxy["score"], "best_proxy_score": best_proxy["score"],
            "temperature": temperature, "updated_weight": weights[name],
        })
    candidate = pd.DataFrame(best_rows.values(), columns=mod.SCHEDULE_COLUMNS).sort_values("TaskID").reset_index(drop=True)
    return candidate, pd.DataFrame(logs), weights, pd.DataFrame(archive).sort_values("iteration")


def make_figures(metrics: pd.DataFrame, hourly: pd.DataFrame, migrations: pd.DataFrame) -> None:
    fig_dir = Q2_ROOT / "figures"; fig_dir.mkdir(parents=True, exist_ok=True)
    colors = ["#CC247C", "#5292F7", "#4EA660"]
    fig, ax = plt.subplots(figsize=(6.4, 4.1))
    for color, row in zip(colors, metrics.itertuples(index=False)):
        ax.scatter(row.carbon_tCO2, row.cost_CNY / 1e9, s=75, color=color, label=row.method)
        ax.annotate(f"{row.mean_latency_ms:.2f} ms", (row.carbon_tCO2, row.cost_CNY / 1e9), xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Carbon emissions (tCO2)"); ax.set_ylabel("Operating cost (billion CNY)"); ax.legend(frameon=False, fontsize=8); fig.tight_layout()
    for ext in ("pdf", "svg", "png"): fig.savefig(fig_dir / f"fig_q2_cost_carbon_latency_probe.{ext}", dpi=400 if ext == "png" else None)
    plt.close(fig)
    region_energy = hourly.groupby(["Method", "Region"], as_index=False).Facility_Load_MW.mean()
    fig, ax = plt.subplots(figsize=(6.4, 4.1))
    methods = list(region_energy.Method.unique()); x = np.arange(6); width = 0.8 / len(methods)
    for i, method in enumerate(methods):
        data = region_energy[region_energy.Method.eq(method)].set_index("Region").reindex([f"Region{x}" for x in "ABCDEF"])
        ax.bar(x + (i - (len(methods)-1)/2)*width, data.Facility_Load_MW, width, label=method, color=colors[i])
    ax.set_xticks(x, [f"Region{x}" for x in "ABCDEF"]); ax.set_ylabel("Mean facility load (MW)"); ax.legend(frameon=False, fontsize=7); fig.tight_layout()
    for ext in ("pdf", "svg", "png"): fig.savefig(fig_dir / f"fig_q2_region_load_probe.{ext}", dpi=400 if ext == "png" else None)
    plt.close(fig)
    counts = migrations.groupby("change_type").size().reindex(["unchanged", "region_only", "time_only", "region_and_time"], fill_value=0)
    fig, ax = plt.subplots(figsize=(6.4, 4.1)); ax.bar(counts.index, counts.values, color=["#79CAFB", "#CC247C", "#F7A24F", "#4EA660"])
    ax.set_ylabel("Task count"); ax.tick_params(axis="x", rotation=20); fig.tight_layout()
    for ext in ("pdf", "svg", "png"): fig.savefig(fig_dir / f"fig_q2_task_migration_probe.{ext}", dpi=400 if ext == "png" else None)
    plt.close(fig)


def main() -> int:
    started = time.perf_counter(); OUT_DIR.mkdir(parents=True, exist_ok=True); mod = load_base()
    tasks, context = mod.load_context()
    incumbent = pd.read_csv(INCUMBENT_PATH); incumbent["Method"] = MAIN_METHOD
    fifo = pd.read_csv(FIFO_PATH)
    first, log, weights, archive = run_alns(mod, tasks, incumbent, context)
    second, _log2, _weights2, _archive2 = run_alns(mod, tasks, incumbent, context)
    deterministic = mod.compare_schedules_exact(first, second)
    incumbent_audit, incumbent_ledger, incumbent_hourly = mod.audit_schedule(incumbent, tasks, context, MAIN_METHOD)
    candidate_audit, candidate_ledger, candidate_hourly = mod.audit_schedule(first, tasks, context, METHOD)
    fifo_audit, _fifo_ledger, fifo_hourly = mod.audit_schedule(fifo, tasks, context, mod.BASELINE_METHOD)
    for audit in (fifo_audit, incumbent_audit, candidate_audit):
        audit["renewable_utilization_attachment_ratio"] = formal_renewable(audit, context)
        audit["renewable_utilization_legacy_facility_denominator_invalid"] = audit.pop("renewable_utilization_ratio")
    merged = incumbent[["TaskID", "ExecutionRegion", "StartMinute"]].merge(first[["TaskID", "ExecutionRegion", "StartMinute"]], on="TaskID", suffixes=("_incumbent", "_alns"), validate="one_to_one")
    merged["change_type"] = np.select([
        merged.ExecutionRegion_incumbent.ne(merged.ExecutionRegion_alns) & merged.StartMinute_incumbent.ne(merged.StartMinute_alns),
        merged.ExecutionRegion_incumbent.ne(merged.ExecutionRegion_alns),
        merged.StartMinute_incumbent.ne(merged.StartMinute_alns),
    ], ["region_and_time", "region_only", "time_only"], default="unchanged")
    first.to_csv(OUT_DIR / "q2_alns_candidate_schedule.csv", index=False)
    log.to_csv(OUT_DIR / "q2_alns_operator_log.csv", index=False)
    archive.to_csv(OUT_DIR / "q2_alns_pareto_proxy_archive.csv", index=False)
    merged.to_csv(OUT_DIR / "q2_alns_task_migrations.csv", index=False)
    dump(OUT_DIR / "q2_alns_constraint_audit.json", candidate_audit)
    probes = mod.risk_probes(METHOD, first, candidate_ledger, tasks, context)
    dump(OUT_DIR / "q2_alns_risk_probes.json", {"status": "PASS" if candidate_audit["passed"] and deterministic else "FAIL", "full_task_audit_passed": candidate_audit["passed"], "deterministic_replay_passed": deterministic, "probes": probes})
    metric_rows = []
    for name, audit in [("FIFO", fifo_audit), ("current", incumbent_audit), ("adaptive_ALNS", candidate_audit)]:
        metric_rows.append({"method": name, "cost_CNY": audit["cost_CNY"], "carbon_tCO2": audit["carbon_tCO2"], "mean_latency_ms": audit["mean_latency_ms"], "renewable_utilization_ratio": audit["renewable_utilization_attachment_ratio"], "hard_audit_passed": audit["passed"]})
    metrics = pd.DataFrame(metric_rows); metrics.to_csv(OUT_DIR / "q2_alns_metrics.csv", index=False)
    hourly = pd.concat([fifo_hourly, incumbent_hourly, candidate_hourly], ignore_index=True); hourly.to_csv(OUT_DIR / "q2_alns_hourly_profiles.csv", index=False)
    objective_keys = ("cost_CNY", "carbon_tCO2", "mean_latency_ms")
    candidate_nonworse = all(
        candidate_audit[key] <= incumbent_audit[key] + 1e-9 for key in objective_keys
    )
    candidate_strictly_better = any(
        candidate_audit[key] < incumbent_audit[key] - 1e-9 for key in objective_keys
    )
    promotion_eligible = (
        candidate_audit["passed"]
        and deterministic
        and candidate_nonworse
        and candidate_strictly_better
    )
    decision = "ROOT_REVIEW_REQUIRED" if promotion_eligible else "PROBE_ONLY"
    dump(OUT_DIR / "q2_alns_summary.json", {"schema_version": 2, "status": "PASS" if candidate_audit["passed"] and deterministic else "FAIL", "method": METHOD, "incumbent": MAIN_METHOD, "search_design": {"iterations": ITERATIONS, "destroy_size": DESTROY_SIZE, "ranking_pool_size": RANKING_POOL_SIZE, "selection": "adaptive roulette wheel", "acceptance": "simulated annealing with geometric cooling", "weight_update": "reaction-factor reward update", "archive": "three-objective non-dominated proxy archive; final schedule is best balanced scalar incumbent"}, "operators": list(weights), "adaptive_weights": weights, "accepted_iteration_count": int(log.accepted.sum()), "improving_iteration_count": int((log.local_score_delta < -1e-9).sum()), "pareto_proxy_archive_size": int(len(archive)), "metrics": metric_rows, "moved_task_count": int(merged.change_type.ne("unchanged").sum()), "deterministic_replay_passed": deterministic, "decision": decision, "formal_main_replaced": False, "runtime_seconds": time.perf_counter() - started, "code_sha256": sha256(Path(__file__).resolve())})
    make_figures(metrics, hourly, merged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
