#!/usr/bin/env python
"""Q3 scarcity-aware adaptive-window rolling binary MILP.

At each block boundary the method chooses 144, 168, or 192 hours by the
observed 24-hour scarcity immediately after each candidate boundary. The
selected block is then solved with the accepted Q3 binary MILP, carrying SOC
between blocks and requiring SOC_T >= SOC_start. No relaxed full-cycle LP is
executed.
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


OUT = Path(__file__).resolve().parent
SEED = 20260809
TOL = 5e-5
WINDOWS = (144, 168, 192)
BOUNDARY_LOOKAHEAD_H = 24
MAX_HOURS = 2407


def find_project_root(path: Path) -> Path:
    for parent in (path, *path.parents):
        if (parent / "contest.yaml").is_file() and (parent / "problems/C/data").is_dir():
            return parent
    raise RuntimeError("cannot locate the Huashu Cup project root")


ROOT = find_project_root(OUT)
Q3_RUNNER = ROOT / "experiments/C/Q3/q3-direct-20260808/models/rolling_milp/run_solver_q3.py"
FIXED_SENSITIVITY = ROOT / "experiments/C/Q3/q3-direct-20260808/sensitivity/q3_sensitivity.csv"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_module(path: Path) -> Any:
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("q3_direct_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import Q3 runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def robust_z(values: np.ndarray) -> np.ndarray:
    median = float(np.median(values))
    q25, q75 = np.quantile(values, [0.25, 0.75])
    scale = max(float(q75 - q25), 1e-9)
    return (values - median) / scale


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, float]:
    data = ROOT / "problems/C/data"
    region = pd.read_excel(data / "region_time_data.xlsx", sheet_name="region_time_data", engine="openpyxl")
    storage = pd.read_excel(data / "storage_information.xlsx", sheet_name="storage_information", engine="openpyxl")
    region = region.sort_values(["Region", "Hour"]).reset_index(drop=True)
    storage["Region"] = storage.Region.astype(str)
    derived_it = region.Baseline_AI_IT_Load_MW.astype(float) + region.NonAI_IT_Load_MW.astype(float)
    region["Derived_IT_Load_MW"] = derived_it
    pue_by_region: dict[str, float] = {}
    for name, group in region.groupby("Region", sort=True):
        positive = group.loc[group.Derived_IT_Load_MW > 1e-9]
        pue_by_region[str(name)] = float(np.median(positive.Total_Load_MW / positive.Derived_IT_Load_MW))
    region["Inferred_PUE"] = region.Region.astype(str).map(pue_by_region)
    region["RecomputedTotalLoad_MW"] = region.Derived_IT_Load_MW * region.Inferred_PUE
    residual = float(np.max(np.abs(region.Total_Load_MW - region.RecomputedTotalLoad_MW)))

    # Robust, dimensionless scarcity index. Larger values mean that retaining
    # energy across the candidate boundary is more valuable.
    pieces: list[pd.DataFrame] = []
    for _, group in region.groupby("Region", sort=True):
        g = group.copy()
        load = g.RecomputedTotalLoad_MW.to_numpy(float)
        renewable = g.AvailableRenewable_MW.to_numpy(float)
        net_ratio = (load - renewable) / np.maximum(load + renewable, 1.0)
        g["ScarcityIndex"] = (
            0.50 * robust_z(g.ElectricityPrice_CNY_per_MWh.to_numpy(float))
            + 0.25 * robust_z(g.CarbonIntensity_tCO2_per_MWh.to_numpy(float))
            + 0.25 * robust_z(net_ratio)
        )
        pieces.append(g)
    return pd.concat(pieces, ignore_index=True), storage, residual


def choose_window(rows: pd.DataFrame, start: int) -> tuple[int, list[dict[str, float]]]:
    remaining = len(rows) - start
    feasible = [h for h in WINDOWS if h <= remaining]
    if not feasible:
        return remaining, [{"horizon_h": float(remaining), "boundary_scarcity": 0.0}]
    scored: list[dict[str, float]] = []
    for horizon in feasible:
        boundary = start + horizon
        future = rows.iloc[boundary : min(boundary + BOUNDARY_LOOKAHEAD_H, len(rows))]
        score = float(future.ScarcityIndex.mean()) if not future.empty else -1e12
        scored.append({"horizon_h": float(horizon), "boundary_scarcity": score})
    # Deterministic tie-breaker prefers 168 h, then the shorter candidate.
    tie_order = {168: 2, 144: 1, 192: 0}
    selected = max(scored, key=lambda x: (x["boundary_scarcity"], tie_order[int(x["horizon_h"])]))
    return int(selected["horizon_h"]), scored


def main() -> int:
    started_at = datetime.now(timezone.utc)
    np.random.seed(SEED)
    q3 = load_module(Q3_RUNNER)
    region, storage, load_residual = load_inputs()
    candidate_parts: list[pd.DataFrame] = []
    trace: list[dict[str, Any]] = []
    block_audits: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    solve_started = time.perf_counter()

    for name in sorted(region.Region.astype(str).unique()):
        rows = region.loc[region.Region.astype(str) == name].sort_values("Hour").reset_index(drop=True)
        if len(rows) != MAX_HOURS:
            raise ValueError(f"{name}: expected {MAX_HOURS} hours, got {len(rows)}")
        st = storage.loc[storage.Region == name].iloc[0]
        current_soc = float(st.InitialSOC_MWh)
        start = 0
        block_id = 0
        while start < len(rows):
            horizon, candidate_scores = choose_window(rows, start)
            frame = rows.iloc[start : start + horizon].copy()
            dispatch, info = q3.solve_dispatch(frame, st, current_soc, current_soc)
            selected_score = next(x["boundary_scarcity"] for x in candidate_scores if int(x["horizon_h"]) == horizon)
            record: dict[str, Any] = {
                "region": name,
                "block_id": block_id,
                "window_start_h": int(frame.Hour.iloc[0]),
                "horizon_h": horizon,
                "initial_SOC_MWh": current_soc,
                "selected_boundary_scarcity": selected_score,
                "candidate_scores_json": json.dumps(candidate_scores, ensure_ascii=False, sort_keys=True),
                "solver_success": bool(info.get("success")),
                "runtime_s": float(info.get("runtime_s") or 0.0),
                "mip_gap": float(info.get("mip_gap") or 0.0),
            }
            if dispatch.empty or not info.get("success"):
                failures.append({**record, "reason": "solver_failed_or_infeasible"})
                break
            dispatch = dispatch.assign(
                Evaluation="adaptive_rolling_block",
                Scenario="observed",
                WindowStart_h=int(frame.Hour.iloc[0]),
                AdaptiveBlockId=block_id,
                AdaptiveHorizon_h=horizon,
            )
            audit = q3.audit(
                dispatch, st, "scarcity_aware_adaptive_window_binary_MILP", horizon,
                current_soc, current_soc, "adaptive_rolling_block",
                int(frame.Hour.iloc[0]), "observed",
            )
            block_audits.append(audit)
            record["terminal_SOC_MWh"] = float(dispatch.SOC_MWh.iloc[-1])
            record["audit_passed"] = bool(audit["passed"])
            trace.append(record)
            if not audit["passed"]:
                failures.append({**record, "reason": "hard_audit_failed"})
                break
            candidate_parts.append(dispatch)
            current_soc = float(dispatch.SOC_MWh.iloc[-1])
            start += horizon
            block_id += 1

    candidate = pd.concat(candidate_parts, ignore_index=True).sort_values(["Region", "Hour"]).reset_index(drop=True)
    complete = not failures and len(candidate) == 6 * MAX_HOURS
    aggregate_audits: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    if complete:
        for name in sorted(candidate.Region.astype(str).unique()):
            st = storage.loc[storage.Region == name].iloc[0]
            cand = candidate.loc[candidate.Region == name].sort_values("Hour").reset_index(drop=True)
            aggregate = q3.audit(
                cand, st, "scarcity_aware_adaptive_window_binary_MILP", len(cand),
                float(st.InitialSOC_MWh), float(st.InitialSOC_MWh),
                "adaptive_rolling_aggregate", 0, "observed",
            )
            aggregate_audits.append(aggregate)
            solver_info = {
                "status": "all adaptive blocks solved", "success": True,
                "runtime_s": float(sum(r["runtime_s"] for r in trace if r["region"] == name)),
                "mip_gap": float(max(r["mip_gap"] for r in trace if r["region"] == name)),
                "solver_mode": "scarcity_aware_adaptive_rolling_binary_MILP",
            }
            metric_rows.append(q3.metrics(
                cand, st, "scarcity_aware_adaptive_window_binary_MILP", len(cand),
                solver_info, "adaptive_rolling_aggregate", 0, "observed",
                float(st.InitialSOC_MWh),
            ))

    candidate.to_csv(OUT / "q3_adaptive_dispatch.csv", index=False, float_format="%.12f")
    pd.DataFrame(trace).to_csv(OUT / "q3_adaptive_window_trace.csv", index=False, float_format="%.12f")
    pd.DataFrame(metric_rows).to_csv(OUT / "q3_adaptive_metrics.csv", index=False, float_format="%.12f")
    audit_doc = {
        "question_id": "Q3",
        "method": "scarcity-aware adaptive-window rolling binary MILP",
        "complete_coverage": complete,
        "candidate_rows": int(len(candidate)),
        "block_count": int(len(trace)),
        "block_audits_passed": bool(block_audits and all(x["passed"] for x in block_audits)),
        "aggregate_audits_passed": bool(aggregate_audits and all(x["passed"] for x in aggregate_audits)),
        "failures": failures,
        "aggregate_audits": aggregate_audits,
        "max_simultaneous_charge_discharge_MW": float(max((x["checks"]["simultaneous_charge_discharge_MW"] for x in block_audits), default=0.0)),
        "max_simultaneous_grid_buy_sell_MW": float(max((x["checks"]["simultaneous_grid_buy_sell_MW"] for x in block_audits), default=0.0)),
        "load_recompute_residual_boundary_MW": load_residual,
        "preserved_legacy_boundary": "269/270; excluded RegionF full-cycle relaxed LP remains non-eligible",
    }
    dump_json(OUT / "q3_adaptive_constraint_audit.json", audit_doc)

    metrics = pd.DataFrame(metric_rows)
    horizon_counts = pd.DataFrame(trace).horizon_h.value_counts().sort_index().to_dict() if trace else {}
    fixed = pd.read_csv(FIXED_SENSITIVITY)
    comparison_rows: list[dict[str, Any]] = []
    for setting_id, group in fixed.groupby("setting_id", sort=False):
        comparison_rows.append({
            "method_id": str(setting_id),
            "method_class": "fixed_window_binary_MILP",
            "total_cost_CNY": float(group.candidate_cost_CNY.sum()),
            "total_carbon_tCO2": float(group.candidate_carbon_tCO2.sum()),
            "max_region_peak_net_import_MW": float(group.candidate_peak_net_import_MW.max()),
            "mean_region_renewable_utilization_ratio": float(group.candidate_renewable_utilization_ratio.mean()),
        })
    comparison_rows.append({
        "method_id": "adaptive_scarcity_boundary",
        "method_class": "adaptive_window_binary_MILP",
        "total_cost_CNY": float(metrics.cost_CNY.sum()),
        "total_carbon_tCO2": float(metrics.carbon_tCO2.sum()),
        "max_region_peak_net_import_MW": float(metrics.peak_net_import_MW.max()),
        "mean_region_renewable_utilization_ratio": float(metrics.renewable_utilization_ratio.mean()),
    })
    comparison = pd.DataFrame(comparison_rows)
    primary = comparison.loc[comparison.method_id == "current_H168_lower_bound"].iloc[0]
    comparison["cost_saving_vs_fixed168_CNY"] = float(primary.total_cost_CNY) - comparison.total_cost_CNY
    comparison["renewable_gain_vs_fixed168"] = (
        comparison.mean_region_renewable_utilization_ratio - float(primary.mean_region_renewable_utilization_ratio)
    )
    comparison.to_csv(OUT / "q3_adaptive_comparison.csv", index=False, float_format="%.12f")
    adaptive_cmp = comparison.loc[comparison.method_id == "adaptive_scarcity_boundary"].iloc[0]
    summary = {
        "schema_version": 1,
        "run_id": "q3-review-20260809",
        "question_id": "Q3",
        "status": "SUCCESS" if complete and audit_doc["block_audits_passed"] and audit_doc["aggregate_audits_passed"] else "FAILED",
        "method": {
            "name": "scarcity-aware adaptive-window rolling binary MILP",
            "candidate_windows_h": list(WINDOWS),
            "boundary_lookahead_h": BOUNDARY_LOOKAHEAD_H,
            "scarcity_weights": {"electricity_price": 0.50, "carbon_intensity": 0.25, "net_load_ratio": 0.25},
            "selection_rule": "choose the candidate boundary with maximum next-24-hour robust scarcity; solve the whole selected block",
            "terminal_rule": "SOC_T >= SOC_start for every selected block",
            "binary_charge_discharge_mutex": True,
        },
        "result": {
            "total_cost_CNY": float(metrics.cost_CNY.sum()) if not metrics.empty else None,
            "total_carbon_tCO2": float(metrics.carbon_tCO2.sum()) if not metrics.empty else None,
            "mean_region_renewable_utilization_ratio": float(metrics.renewable_utilization_ratio.mean()) if not metrics.empty else None,
            "max_region_peak_net_import_MW": float(metrics.peak_net_import_MW.max()) if not metrics.empty else None,
            "total_runtime_s": float(time.perf_counter() - solve_started),
            "horizon_counts": {str(int(k)): int(v) for k, v in horizon_counts.items()},
            "cost_saving_vs_fixed168_CNY": float(adaptive_cmp.cost_saving_vs_fixed168_CNY),
            "renewable_gain_vs_fixed168": float(adaptive_cmp.renewable_gain_vs_fixed168),
        },
        "eligibility": {
            "eligible_for_model_review": bool(complete and audit_doc["block_audits_passed"] and audit_doc["aggregate_audits_passed"]),
            "not_automatically_primary": True,
            "no_global_optimality_claim": True,
            "excluded_relaxed_lp_probe_preserved": True,
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    dump_json(OUT / "q3_adaptive_summary.json", summary)

    outputs = [
        OUT / "q3_adaptive_dispatch.csv", OUT / "q3_adaptive_window_trace.csv",
        OUT / "q3_adaptive_metrics.csv", OUT / "q3_adaptive_constraint_audit.json",
        OUT / "q3_adaptive_comparison.csv", OUT / "q3_adaptive_summary.json", Path(__file__).resolve(),
    ]
    manifest = {
        "schema_version": 1,
        "run_id": "q3-adaptive-window-20260809",
        "command": "python experiments/C/Q3/q3-review-20260809/run_q3_adaptive_window.py",
        "seed": SEED,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "code_source": {"path": str(Q3_RUNNER.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(Q3_RUNNER)},
        "inputs": [
            {"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(p)}
            for p in [
                ROOT / "problems/C/data/region_time_data.xlsx",
                ROOT / "problems/C/data/storage_information.xlsx",
                FIXED_SENSITIVITY,
            ]
        ],
        "outputs": [
            {"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(p), "bytes": p.stat().st_size}
            for p in outputs
        ],
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    dump_json(OUT / "run_manifest.json", manifest)
    return 0 if summary["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
