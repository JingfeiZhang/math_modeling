#!/usr/bin/env python
"""Q4 low-renewable peak-budget experiment on the repaired 24-hour envelope."""
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
SPRINT_ID = "sprint-20260808T051118704690Z"
TASK_ID = "solver-q4"
TASK_PACKAGE = ROOT / "sprints" / SPRINT_ID / "tasks" / f"{TASK_ID}.json"
REPAIRED_RUNNER = (
    ROOT
    / "sprints"
    / "sprint-20260808T023235447353Z"
    / "merged"
    / "solver-q4"
    / "run_solver_q4_enhanced.py"
)
INTEGRATED_RUNNER = (
    ROOT
    / "sprints"
    / "sprint-20260808T031214934335Z"
    / "merged"
    / "solver-q4"
    / "run_solver_q4_final.py"
)
HORIZON = 24
RENEWABLE_MULTIPLIER = 0.70
CARBON_WEIGHT = 0.50
WEIGHTS = [
    0.0,
    1e-7,
    3e-7,
    1e-6,
    3e-6,
    1e-5,
    3e-5,
    1e-4,
    3e-4,
    5e-4,
    7e-4,
    1e-3,
    1e-2,
    5e-2,
    1e-1,
    2e-1,
    5e-1,
]
TOL = 5e-5
PEAK_TOL = 1e-6


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def directory_hash(path: Path) -> str:
    source = "\n".join(
        f"{item.relative_to(path).as_posix()}:{sha256_file(item)}"
        for item in sorted(path.rglob("*"))
        if item.is_file()
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def verify_inputs(task: dict[str, Any]) -> None:
    failures: list[dict[str, Any]] = []
    for item in task.get("input_hashes", []):
        path = ROOT / str(item["path"])
        if item.get("kind") == "directory" and path.is_dir():
            observed = directory_hash(path)
        elif path.is_file():
            observed = sha256_file(path)
        else:
            observed = None
        if observed != item.get("sha256"):
            failures.append(
                {
                    "path": item["path"],
                    "expected": item.get("sha256"),
                    "observed": observed,
                }
            )
    if failures:
        raise RuntimeError(
            "stale or missing sprint inputs: "
            + json.dumps(failures, ensure_ascii=False)
        )


def dump_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def load_module(name: str, path: Path) -> Any:
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dispatch_metrics(
    dispatch: pd.DataFrame,
    solver: dict[str, Any],
    peak_weight: float,
    total_import_cap: float,
) -> dict[str, Any]:
    cost = float(
        np.dot(dispatch.GridPurchase_MW, dispatch.ElectricityPrice_CNY_per_MWh)
        - np.dot(dispatch.GridSell_MW, dispatch.SellPrice_CNY_per_MWh)
    )
    carbon = float(
        np.dot(dispatch.GridPurchase_MW, dispatch.CarbonIntensity_tCO2_per_MWh)
    )
    peak = float(dispatch.groupby("Hour").NetGridImport_MW.sum().max())
    positive_peak = max(peak, 0.0)
    raw_peak_variable = float(solver["system_peak_variable_MW"])
    peak_epigraph_tight = abs(raw_peak_variable - positive_peak) <= TOL
    linked_peak_variable = raw_peak_variable if peak_epigraph_tight else positive_peak
    renewable_total = float(dispatch.AvailableRenewable_MW.sum())
    renewable_used = renewable_total - float(dispatch.Curtailment_MW.sum())
    penalty = peak_weight / max(total_import_cap, 1.0) * raw_peak_variable
    composite_without_peak = float(solver["objective"]) - penalty
    return {
        "peak_weight": peak_weight,
        "normalized_peak_coefficient_per_MW": peak_weight
        / max(total_import_cap, 1.0),
        "solver_success": bool(solver["success"]),
        "solver_status": str(solver["status"]),
        "runtime_s": float(solver["runtime_s"]),
        "mip_gap": solver.get("mip_gap"),
        "solver_objective_with_peak": float(solver["objective"]),
        "composite_objective_without_peak": composite_without_peak,
        "system_peak_variable_MW": linked_peak_variable,
        "raw_solver_peak_variable_MW": raw_peak_variable,
        "peak_epigraph_tight": peak_epigraph_tight,
        "system_signed_peak_net_import_MW": peak,
        "system_positive_peak_MW": positive_peak,
        "cost_CNY": cost,
        "carbon_tCO2": carbon,
        "renewable_utilization_ratio": renewable_used
        / max(renewable_total, 1e-12),
        "system_net_import_std_MW": float(
            dispatch.groupby("Hour").NetGridImport_MW.sum().std(ddof=0)
        ),
    }


def main() -> int:
    started = time.perf_counter()
    STAGING.mkdir(parents=True, exist_ok=True)
    task = json.loads(TASK_PACKAGE.read_text(encoding="utf-8"))
    verify_inputs(task)

    repaired = load_module("q4_repaired_source", REPAIRED_RUNNER)
    integrated = load_module("q4_integrated_source", INTEGRATED_RUNNER)
    base, storage_table, repaired_provenance = repaired.load_inputs()
    if len(base) != 6 * HORIZON:
        raise ValueError(f"expected 144 region-hour rows, observed {len(base)}")

    low_renewable = base.copy()
    low_renewable["AvailableRenewable_MW"] = (
        low_renewable.AvailableRenewable_MW.astype(float) * RENEWABLE_MULTIPLIER
    )
    integrated.HORIZON = HORIZON
    integrated.CARBON_WEIGHT = CARBON_WEIGHT
    total_import_cap = float(storage_table.MaxGridImport_MW.sum())

    rows: list[dict[str, Any]] = []
    audits: dict[str, Any] = {}
    dispatches: dict[float, pd.DataFrame] = {}
    for peak_weight in WEIGHTS:
        integrated.PEAK_WEIGHT = peak_weight
        dispatch, solver = integrated.solve_integrated(low_renewable, storage_table)
        if dispatch.empty or not solver.get("success"):
            raise RuntimeError(f"integrated MILP failed for weight={peak_weight}: {solver}")
        observed_positive_peak = max(
            float(dispatch.groupby("Hour").NetGridImport_MW.sum().max()), 0.0
        )
        raw_peak_variable = float(solver["system_peak_variable_MW"])
        peak_epigraph_tight = abs(raw_peak_variable - observed_positive_peak) <= TOL
        audit = integrated.audit_dispatch(
            dispatch,
            storage_table,
            f"integrated_binary_MILP_peak_weight_{peak_weight:.7g}",
            raw_peak_variable if peak_epigraph_tight else None,
        )
        if not audit.get("passed"):
            raise RuntimeError(f"hard audit failed for weight={peak_weight}")
        record = dispatch_metrics(dispatch, solver, peak_weight, total_import_cap)
        record["audit_passed"] = True
        rows.append(record)
        audits[f"{peak_weight:.7g}"] = audit
        dispatches[peak_weight] = dispatch

    tradeoff = pd.DataFrame(rows).sort_values("peak_weight").reset_index(drop=True)
    base_row = tradeoff.iloc[0]
    base_peak = float(base_row.system_positive_peak_MW)
    minimum_peak = float(tradeoff.system_positive_peak_MW.min())
    if base_peak - minimum_peak <= PEAK_TOL:
        raise RuntimeError("peak price is inactive across the declared parameter scan")
    target_peak = minimum_peak + 0.5 * (base_peak - minimum_peak)
    eligible = tradeoff[
        (tradeoff.peak_weight > 0)
        & (tradeoff.system_positive_peak_MW <= target_peak + PEAK_TOL)
        & tradeoff.peak_epigraph_tight
        & tradeoff.audit_passed
    ]
    if eligible.empty:
        raise RuntimeError("no audited nonzero peak price meets the data-derived budget")
    selected_row = eligible.sort_values("peak_weight").iloc[0]
    selected_weight = float(selected_row.peak_weight)
    selected_peak = float(selected_row.system_positive_peak_MW)
    selected_dispatch = dispatches[selected_weight].copy()

    inactive = tradeoff[
        (tradeoff.peak_weight < selected_weight)
        & (
            np.abs(tradeoff.system_positive_peak_MW - base_peak)
            <= PEAK_TOL
        )
    ]
    lower_break_weight = float(inactive.peak_weight.max()) if not inactive.empty else 0.0
    peak_reduction = base_peak - selected_peak
    composite_delta = float(selected_row.composite_objective_without_peak) - float(
        base_row.composite_objective_without_peak
    )
    discrete_marginal = composite_delta / peak_reduction
    if selected_weight <= 0 or peak_reduction <= PEAK_TOL or discrete_marginal <= 0:
        raise RuntimeError(
            "selected peak budget did not produce a positive discrete marginal price"
        )

    baseline_frames = []
    storage_lookup = {
        str(row.Region): pd.Series(row._asdict())
        for row in storage_table.itertuples(index=False)
    }
    for region in sorted(base.Region.astype(str).unique()):
        baseline_frames.append(
            repaired.baseline_dispatch(
                base[base.Region.astype(str) == region].copy(),
                storage_lookup[region],
                RENEWABLE_MULTIPLIER,
            )
        )
    baseline = pd.concat(baseline_frames, ignore_index=True)
    baseline_peak = float(baseline.groupby("Hour").NetGridImport_MW.sum().max())

    tradeoff.to_csv(
        STAGING / "q4_peak_tradeoff.csv", index=False, float_format="%.12f"
    )
    selected_dispatch.to_csv(
        STAGING / "q4_peak_selected_dispatch.csv",
        index=False,
        float_format="%.10f",
    )
    dump_json(STAGING / "q4_peak_constraint_audit.json", audits)

    summary = {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q4",
        "status": "PASS",
        "scope": "24-hour low-renewable probe on the repaired Q4 envelope",
        "method": {
            "name": "integrated six-region binary MILP peak-price scan",
            "renewable_multiplier": RENEWABLE_MULTIPLIER,
            "carbon_weight": CARBON_WEIGHT,
            "peak_weights": WEIGHTS,
            "target_rule": "midpoint between the zero-price peak and the minimum audited peak observed on the declared scan",
            "optimality_boundary": "Each scan point is an integrated storage MILP with fixed upstream task assignment; no joint task-storage or full-horizon optimality claim.",
        },
        "provenance": {
            "repaired_q4_directory": "sprints/sprint-20260808T023235447353Z/merged/solver-q4",
            "repaired_q4_directory_sha256": directory_hash(REPAIRED_RUNNER.parent),
            "integrated_q4_directory": "sprints/sprint-20260808T031214934335Z/merged/solver-q4",
            "integrated_q4_directory_sha256": directory_hash(INTEGRATED_RUNNER.parent),
            "repaired_input_provenance": repaired_provenance,
        },
        "coordination_result": {
            "zero_price_peak_MW": base_peak,
            "minimum_audited_peak_MW": minimum_peak,
            "data_derived_target_peak_MW": target_peak,
            "selected_peak_weight": selected_weight,
            "selected_normalized_peak_coefficient_per_MW": float(
                selected_row.normalized_peak_coefficient_per_MW
            ),
            "selected_peak_MW": selected_peak,
            "peak_reduction_MW": peak_reduction,
            "inactive_to_active_weight_bracket": [
                lower_break_weight,
                selected_weight,
            ],
            "discrete_marginal_composite_price_per_MW": discrete_marginal,
            "composite_objective_delta_without_peak": composite_delta,
            "selected_cost_delta_CNY": float(selected_row.cost_CNY)
            - float(base_row.cost_CNY),
            "selected_carbon_delta_tCO2": float(selected_row.carbon_tCO2)
            - float(base_row.carbon_tCO2),
            "baseline_no_storage_peak_MW": baseline_peak,
            "price_signal_active": True,
        },
        "hard_audit": {
            "all_scan_points_passed": bool(tradeoff.audit_passed.all()),
            "scan_point_count": int(len(tradeoff)),
            "selected_weight_audit_key": f"{selected_weight:.7g}",
            "charge_discharge_mutex_checked": True,
            "grid_import_export_mutex_checked": True,
            "terminal_soc_checked": True,
            "system_peak_linkage_checked": True,
        },
        "claim_proposals": [
            {
                "id": "Q4-PEAK-P1",
                "status": "proposal_only",
                "text": "In the bounded low-renewable probe, a data-derived peak budget activated a nonzero discrete marginal peak signal while all audited storage, grid, and system-peak constraints remained satisfied.",
            },
            {
                "id": "Q4-PEAK-P2",
                "status": "proposal_only",
                "text": "The peak-price result is a discrete MILP trade-off on a fixed task envelope, not an LP dual, full-horizon result, or globally joint task-storage optimum.",
            },
        ],
        "limitations": [
            "The marginal value is a finite discrete composite-objective estimate, not a continuous LP dual variable.",
            "The target is derived only from the declared low-renewable 24-hour scan.",
            "Upstream task assignments are fixed and physical inter-region power flow is excluded.",
            "Formal claim freezing remains root-owned.",
        ],
    }
    dump_json(STAGING / "q4_peak_summary.json", summary)

    output_names = [
        "q4_peak_tradeoff.csv",
        "q4_peak_selected_dispatch.csv",
        "q4_peak_constraint_audit.json",
        "q4_peak_summary.json",
    ]
    manifest = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "run_id": "q4-peak-budget-20260808",
        "question_id": "Q4",
        "engine": "python-scipy-highs-milp",
        "command": [sys.executable, str(STAGING / "run_q4_peak_budget.py")],
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": __import__("scipy").__version__,
        },
        "seed": None,
        "input_hashes": task["input_hashes"],
        "code": {
            "runner": (STAGING / "run_q4_peak_budget.py")
            .relative_to(ROOT)
            .as_posix(),
            "sha256": sha256_file(STAGING / "run_q4_peak_budget.py"),
        },
        "outputs": output_names,
        "status": "PASS",
        "runtime_s": round(time.perf_counter() - started, 6),
        "generated_at_utc": utcnow(),
    }
    dump_json(STAGING / "q4_peak_run_manifest.json", manifest)

    artifact_names = output_names + [
        "q4_peak_run_manifest.json",
        "run_q4_peak_budget.py",
    ]
    artifacts = [
        {
            "path": (STAGING / name).relative_to(ROOT).as_posix(),
            "sha256": sha256_file(STAGING / name),
        }
        for name in artifact_names
    ]
    handoff = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "attempt": int(task.get("attempt", 1)),
        "status": "SUCCESS",
        "input_hashes": task["input_hashes"],
        "written_paths": [item["path"] for item in artifacts]
        + [(STAGING / "handoff.json").relative_to(ROOT).as_posix()],
        "artifacts": artifacts,
        "gate_result": {
            "gate": "G5",
            "passed": True,
            "checks": [
                "input_hashes_rechecked",
                "data_derived_peak_budget",
                "nonzero_discrete_marginal_price",
                "integrated_binary_storage_MILP",
                "all_scan_hard_audits",
                "charge_discharge_mutex",
                "grid_import_export_mutex",
                "terminal_soc",
                "system_peak_linkage",
                "artifact_hashes",
            ],
        },
        "summary": "The low-renewable peak-budget scan found an audited nonzero discrete marginal peak signal without forcing an arbitrary target.",
    }
    dump_json(STAGING / "handoff.json", handoff)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        (STAGING / "q4_peak_failure.log").write_text(
            f"{type(exc).__name__}: {exc}\n", encoding="utf-8"
        )
        raise
