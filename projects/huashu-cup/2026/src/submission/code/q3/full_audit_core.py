#!/usr/bin/env python
"""Replace the excluded Q3 relaxed-LP probe with a full-horizon binary MILP audit.

The accepted 264 candidate/baseline audits are preserved byte-for-byte from the
frozen evidence. Only the six validation-only full-cycle probes are recomputed.
Performance metrics from this probe remain outside the Q3 performance claims.
"""
from __future__ import annotations

# 本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：OpenAI Codex，版本/型号：GPT-5，开发机构/公司：OpenAI，版本发布日期：2025-08-07。

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix, hstack, lil_matrix, vstack


SEED = 20260809
TOL = 5e-5
TIME_LIMIT_S = 300.0
EXPECTED_REGIONS = [f"Region{letter}" for letter in "ABCDEF"]
EXPECTED_HOURS_PER_REGION = 2407
EXPECTED_LEGACY_FORMAL_AUDITS = 264
EXPECTED_TOTAL_AUDITS = 270
CORE_OUTPUTS = [
    "full_cycle_binary_dispatch.csv",
    "full_cycle_baseline_dispatch.csv",
    "full_cycle_binary_metrics.csv",
    "full_cycle_baseline_metrics.csv",
    "full_cycle_binary_audit.json",
    "full_cycle_baseline_audit.json",
    "constraint_audit.json",
    "summary.json",
    "claim_proposals.json",
]


SCRIPT = Path(__file__).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def relative(path: Path) -> str:
    return path.name


def verify_pinned_inputs(input_dir: Path) -> list[dict[str, Any]]:
    names = ["region_time_data.xlsx", "storage_information.xlsx", "power_mapping.xlsx"]
    return [{"path": name, "sha256": sha256_file(input_dir / name)} for name in names]


def load_inputs(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    region = pd.read_excel(
        data_dir / "region_time_data.xlsx", sheet_name="region_time_data", engine="openpyxl"
    )
    storage = pd.read_excel(
        data_dir / "storage_information.xlsx", sheet_name="storage_information", engine="openpyxl"
    )
    region = region.sort_values(["Region", "Hour"]).reset_index(drop=True)
    storage["Region"] = storage.Region.astype(str)
    region["Region"] = region.Region.astype(str)
    region["Derived_IT_Load_MW"] = (
        region.Baseline_AI_IT_Load_MW.astype(float) + region.NonAI_IT_Load_MW.astype(float)
    )
    pue_by_region: dict[str, float] = {}
    for name, group in region.groupby("Region", sort=True):
        positive = group.loc[group.Derived_IT_Load_MW > 1e-9]
        pue_by_region[str(name)] = float(
            np.median(positive.Total_Load_MW.astype(float) / positive.Derived_IT_Load_MW.astype(float))
        )
    region["Inferred_PUE"] = region.Region.map(pue_by_region)
    region["RecomputedTotalLoad_MW"] = region.Derived_IT_Load_MW * region.Inferred_PUE
    regions = sorted(region.Region.unique().tolist())
    if regions != EXPECTED_REGIONS:
        raise ValueError(f"region set changed: {regions}")
    counts = region.groupby("Region").size().to_dict()
    if any(counts.get(name) != EXPECTED_HOURS_PER_REGION for name in EXPECTED_REGIONS):
        raise ValueError(f"hour coverage changed: {counts}")
    return region, storage


def stable_solver_info(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "optimal full-horizon binary MILP",
        "success": bool(info.get("success")),
        "runtime_s": 0.0,
        "mip_gap": info.get("mip_gap"),
        "solver_mode": "full_cycle_binary_MILP_audit_probe",
    }


# BEGIN APPENDIX_Q3_FULL_AUDIT_MUTEX
# BEGIN APPENDIX_Q3_AUDIT_VARIABLES
def solve_full_horizon_binary(
    q3: Any,
    frame: pd.DataFrame,
    storage: pd.Series,
    initial_soc: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Solve the regional full horizon with explicit storage and grid mutexes."""

    baseline = q3.build_baseline(frame, storage, initial_soc)
    objective, bounds, constraints, integrality, slices = q3.make_model(
        frame, storage, baseline, initial_soc, initial_soc
    )
    horizon = len(frame)
    original_nvar = len(objective)
    grid_mode = slice(original_nvar, original_nvar + horizon)
    import_limit = float(storage.MaxGridImport_MW)
    export_limit = float(min(storage.SellLimit_MW, storage.MaxGridExport_MW))

    extended_objective = np.concatenate([objective, np.zeros(horizon)])
    extended_bounds = Bounds(
        np.concatenate([np.asarray(bounds.lb), np.zeros(horizon)]),
        np.concatenate([np.asarray(bounds.ub), np.ones(horizon)]),
    )
    extended_integrality = np.concatenate([integrality, np.ones(horizon)])

    original_matrix = hstack(
        [constraints.A, csr_matrix((constraints.A.shape[0], horizon))], format="csr"
    )
    mutex_matrix = lil_matrix((2 * horizon, original_nvar + horizon), dtype=float)
    mutex_lower = np.full(2 * horizon, -np.inf)
    mutex_upper = np.empty(2 * horizon)
    for t in range(horizon):
        buy_row = 2 * t
        sell_row = buy_row + 1
        mutex_matrix[buy_row, slices["grid_load"].start + t] = 1.0
        mutex_matrix[buy_row, slices["grid_charge"].start + t] = 1.0
        mutex_matrix[buy_row, grid_mode.start + t] = -import_limit
        mutex_upper[buy_row] = 0.0

        mutex_matrix[sell_row, slices["sell"].start + t] = 1.0
        mutex_matrix[sell_row, grid_mode.start + t] = export_limit
        mutex_upper[sell_row] = export_limit

# END APPENDIX_Q3_AUDIT_VARIABLES
# BEGIN APPENDIX_Q3_AUDIT_MUTEX_SOLVE

    extended_constraints = LinearConstraint(
        vstack([original_matrix, mutex_matrix.tocsr()], format="csr"),
        np.concatenate([np.asarray(constraints.lb), mutex_lower]),
        np.concatenate([np.asarray(constraints.ub), mutex_upper]),
    )

    started = time.perf_counter()
    result = milp(
        c=extended_objective,
        integrality=extended_integrality,
        bounds=extended_bounds,
        constraints=extended_constraints,
        options={"presolve": True, "time_limit": TIME_LIMIT_S, "mip_rel_gap": 1e-7},
    )
    runtime = time.perf_counter() - started
    info = {
        "status": str(result.message),
        "success": bool(result.success and result.x is not None),
        "runtime_s": runtime,
        "mip_gap": q3.finite(getattr(result, "mip_gap", None)),
        "objective": q3.finite(getattr(result, "fun", None)),
        "mip_node_count": int(getattr(result, "mip_node_count", 0) or 0),
        "solver_mode": "full_cycle_binary_MILP_double_mutex_audit_probe",
    }
    if not info["success"]:
        return pd.DataFrame(), info

# END APPENDIX_Q3_AUDIT_MUTEX_SOLVE
# BEGIN APPENDIX_Q3_AUDIT_RECONSTRUCT

    x = result.x
    data = frame.sort_values("Hour").reset_index(drop=True)
    charge = x[slices["charge"]]
    discharge = x[slices["discharge"]]
    grid_charge = x[slices["grid_charge"]]
    grid_load = x[slices["grid_load"]]
    sell = x[slices["sell"]]
    dispatch = pd.DataFrame(
        {
            "Hour": data.Hour.astype(int),
            "Region": data.Region.astype(str),
            "AvailableRenewable_MW": data.AvailableRenewable_MW.astype(float),
            "Total_Load_MW": data.RecomputedTotalLoad_MW.astype(float),
            "ElectricityPrice_CNY_per_MWh": data.ElectricityPrice_CNY_per_MWh.astype(float),
            "SellPrice_CNY_per_MWh": data.SellPrice_CNY_per_MWh.astype(float),
            "CarbonIntensity_tCO2_per_MWh": data.CarbonIntensity_tCO2_per_MWh.astype(float),
            "ChargePower_MW": charge,
            "DischargePower_MW": x[slices["discharge"]],
            "SOC_MWh": x[slices["soc"]],
            "RenewableToLoad_MW": x[slices["renewable_to_load"]],
            "RenewableCharge_MW": x[slices["renewable_charge"]],
            "GridCharge_MW": grid_charge,
            "GridPurchase_MW": grid_load + grid_charge,
            "GridLoadPurchase_MW": grid_load,
            "GridSell_MW": sell,
            "Curtailment_MW": x[slices["curtail"]],
            "NetGridImport_MW": grid_load + grid_charge - sell,
            "GridEnergyForCost_MW": grid_load + grid_charge,
            "ChargeMode": np.rint(x[slices["mode"]]).astype(int),
            "GridImportMode": np.rint(x[grid_mode]).astype(int),
        }
    )
    return dispatch, info
# END APPENDIX_Q3_AUDIT_RECONSTRUCT
# END APPENDIX_Q3_FULL_AUDIT_MUTEX


def generate(input_dir: Path, output_dir: Path, seed: int = SEED) -> int:
    started_at = datetime.now(timezone.utc)
    started_clock = time.perf_counter()
    np.random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    from code.q3 import storage_core as q3
    q3.TIME_LIMIT_S = TIME_LIMIT_S
    pinned_inputs = verify_pinned_inputs(input_dir)
    region_data, storage_data = load_inputs(input_dir)
    legacy_audit_path = output_dir / "q3_constraint_audit.json"
    legacy_summary_path = output_dir / "q3_summary.json"
    legacy_doc = load_json(legacy_audit_path)
    legacy_audits = list(legacy_doc["audits"])
    legacy_formal = [row for row in legacy_audits if row.get("evaluation") != "full_cycle_probe"]
    legacy_probe = [row for row in legacy_audits if row.get("evaluation") == "full_cycle_probe"]
    if len(legacy_audits) != EXPECTED_TOTAL_AUDITS or len(legacy_probe) != 6:
        raise ValueError("legacy 270-audit structure changed")
    if len(legacy_formal) != EXPECTED_LEGACY_FORMAL_AUDITS or not all(
        row.get("passed") is True for row in legacy_formal
    ):
        raise ValueError("legacy formal audits are not the expected 264/264 pass set")

    candidate_parts: list[pd.DataFrame] = []
    baseline_parts: list[pd.DataFrame] = []
    candidate_metrics: list[dict[str, Any]] = []
    baseline_metrics: list[dict[str, Any]] = []
    candidate_audits: list[dict[str, Any]] = []
    baseline_audits: list[dict[str, Any]] = []
    solver_records: list[dict[str, Any]] = []

    for name in EXPECTED_REGIONS:
        frame = region_data.loc[region_data.Region == name].sort_values("Hour").reset_index(drop=True)
        storage = storage_data.loc[storage_data.Region == name].iloc[0]
        initial_soc = float(storage.InitialSOC_MWh)
        dispatch, info = solve_full_horizon_binary(q3, frame, storage, initial_soc)
        if dispatch.empty or not info.get("success"):
            raise RuntimeError(f"{name}: full-horizon binary MILP failed: {info}")
        audit = q3.audit(
            dispatch,
            storage,
            "full_cycle_binary_MILP_audit_probe",
            len(frame),
            initial_soc,
            initial_soc,
            "full_cycle_probe",
            0,
            "observed",
        )
        if not audit["passed"]:
            raise RuntimeError(f"{name}: corrected probe failed hard audit: {audit}")
        baseline = q3.build_baseline(frame, storage, initial_soc)
        baseline_audit = q3.audit(
            baseline,
            storage,
            "no_storage_renewable_first",
            len(frame),
            initial_soc,
            initial_soc,
            "full_cycle_baseline_reference",
            0,
            "observed",
        )
        if not baseline_audit["passed"]:
            raise RuntimeError(f"{name}: same-output baseline failed audit: {baseline_audit}")
        stable_info = stable_solver_info(info)
        candidate_metrics.append(
            q3.metrics(
                dispatch,
                storage,
                "full_cycle_binary_MILP_audit_probe",
                len(frame),
                stable_info,
                "full_cycle_probe",
                0,
                "observed",
                initial_soc,
            )
        )
        baseline_info = {
            "status": "deterministic no-storage baseline",
            "success": True,
            "runtime_s": 0.0,
            "mip_gap": None,
            "solver_mode": "baseline",
        }
        baseline_metrics.append(
            q3.metrics(
                baseline,
                storage,
                "no_storage_renewable_first",
                len(frame),
                baseline_info,
                "full_cycle_baseline_reference",
                0,
                "observed",
                initial_soc,
            )
        )
        candidate_audits.append(audit)
        baseline_audits.append(baseline_audit)
        candidate_parts.append(
            dispatch.assign(
                Evaluation="full_cycle_probe",
                Scenario="observed",
                WindowStart_h=0,
                Method="full_cycle_binary_MILP_audit_probe",
            )
        )
        baseline_parts.append(
            baseline.assign(
                Evaluation="full_cycle_baseline_reference",
                Scenario="observed",
                WindowStart_h=0,
                Method="no_storage_renewable_first",
            )
        )
        solver_records.append(
            {
                "region": name,
                "success": True,
                "status": str(info.get("status")),
                "mip_gap": info.get("mip_gap"),
                "objective": info.get("objective"),
                "mip_node_count": info.get("mip_node_count"),
                "solver_mode": "full_cycle_binary_MILP_audit_probe",
            }
        )

    complete_audits = legacy_formal + candidate_audits
    if len(complete_audits) != EXPECTED_TOTAL_AUDITS:
        raise AssertionError(f"expected 270 complete audits, got {len(complete_audits)}")
    passed_count = sum(row.get("passed") is True for row in complete_audits)
    all_passed = passed_count == EXPECTED_TOTAL_AUDITS
    if not all_passed:
        raise AssertionError(f"complete audit set is {passed_count}/{EXPECTED_TOTAL_AUDITS}")

    candidate_dispatch = pd.concat(candidate_parts, ignore_index=True)
    baseline_dispatch = pd.concat(baseline_parts, ignore_index=True)
    candidate_dispatch.to_csv(
        output_dir / "full_cycle_binary_dispatch.csv", index=False, float_format="%.12f"
    )
    baseline_dispatch.to_csv(
        output_dir / "full_cycle_baseline_dispatch.csv", index=False, float_format="%.12f"
    )
    pd.DataFrame(candidate_metrics).to_csv(
        output_dir / "full_cycle_binary_metrics.csv", index=False, float_format="%.12f"
    )
    pd.DataFrame(baseline_metrics).to_csv(
        output_dir / "full_cycle_baseline_metrics.csv", index=False, float_format="%.12f"
    )
    dump_json(
        output_dir / "full_cycle_binary_audit.json",
        {"schema_version": 1, "tolerance": TOL, "audits": candidate_audits},
    )
    dump_json(
        output_dir / "full_cycle_baseline_audit.json",
        {"schema_version": 1, "tolerance": TOL, "audits": baseline_audits},
    )
    dump_json(
        output_dir / "constraint_audit.json",
        {
            "schema_version": 2,
            "tolerance": TOL,
            "audit_set_definition": (
                "264 unchanged formal candidate/baseline audits plus six recomputed "
                "regional full-horizon binary-MILP audit probes"
            ),
            "audits": complete_audits,
        },
    )
    max_simultaneous = max(
        row["checks"]["simultaneous_charge_discharge_MW"] for row in candidate_audits
    )
    max_gap = max(float(row["mip_gap"] or 0.0) for row in solver_records)
    summary = {
        "schema_version": 2,
        "project_id": "huashu-cup-2026",
        "problem_id": "C",
        "question_id": "Q3",
        "run_id": "q3-full-audit-fix-20260809",
        "candidate_status": "CANDIDATE",
        "method": {
            "name": "six-region independent full-horizon binary-MILP audit probe",
            "hours_per_region": EXPECTED_HOURS_PER_REGION,
            "binary_charge_discharge_mutex": True,
            "binary_grid_import_export_mutex": True,
            "combined_grid_import_cap": True,
            "terminal_rule": "terminal SOC >= initial SOC",
            "time_limit_s_per_region": TIME_LIMIT_S,
            "mip_rel_gap": 1e-7,
        },
        "audit_boundary": {
            "legacy_formal_audit_count": len(legacy_formal),
            "legacy_formal_audits_passed": len(legacy_formal),
            "corrected_full_cycle_probe_count": len(candidate_audits),
            "corrected_full_cycle_probes_passed": sum(
                row["passed"] is True for row in candidate_audits
            ),
            "total_audit_count": len(complete_audits),
            "total_audits_passed": passed_count,
            "all_270_audits_passed": all_passed,
            "same_output_baseline_audits_passed": all(
                row["passed"] is True for row in baseline_audits
            ),
            "maximum_simultaneous_charge_discharge_MW": max_simultaneous,
            "maximum_mip_gap": max_gap,
        },
        "solver_records": solver_records,
        "interpretation_limits": [
            "The six full-horizon models are solved independently by region; no inter-region power flow is modeled.",
            "The corrected probe supports feasibility and audit completeness, not a new performance comparison.",
            "The result does not establish a single system-wide full-horizon global optimum.",
            "The previous relaxed-LP 269/270 result remains historical evidence and is superseded only for the formal audit boundary.",
        ],
        "sources": {
            "base_runner": {"path": "code/q3/storage_core.py", "sha256": sha256_file(Path(q3.__file__))},
            "rolling_audit": {"path": legacy_audit_path.name, "sha256": sha256_file(legacy_audit_path)},
            "rolling_summary": {"path": legacy_summary_path.name, "sha256": sha256_file(legacy_summary_path)},
            "pinned_inputs": pinned_inputs,
        },
    }
    dump_json(output_dir / "summary.json", summary)
    dump_json(
        output_dir / "claim_proposals.json",
        {
            "schema_version": 1,
            "question_id": "Q3",
            "status": "PROPOSAL_ONLY",
            "claims": [
                {
                    "id": "Q3-ALL-270-AUDITS-PASS",
                    "statement": (
                        f"All {passed_count} Q3 audits pass after replacing the relaxed "
                        "full-cycle LP probe with six regional full-horizon binary-MILP "
                        "feasibility probes."
                    ),
                    "locator": "summary.json:$.audit_boundary.total_audits_passed",
                    "value": passed_count,
                    "unit": "audit",
                    "boundary": (
                        "The full-horizon probes are regional feasibility checks and do not prove "
                        "one system-wide global optimum or support a new performance claim."
                    ),
                }
            ],
        },
    )

    finished_at = datetime.now(timezone.utc)
    duration_seconds = time.perf_counter() - started_clock
    artifacts = [
        {"path": relative(output_dir / name), "sha256": sha256_file(output_dir / name)}
        for name in CORE_OUTPUTS
    ]
    manifest = {
        "schema_version": 1,
        "run_id": "q3-full-audit-fix-20260809",
        "problem_id": "C",
        "question_id": "Q3",
        "candidate_status": "CANDIDATE",
        "engine": "python/scipy.optimize.milp (HiGHS)",
        "command": ["python", "code/q3/run_q3.py"],
        "working_directory": "submission output directory",
        "random_seed": seed,
        "determinism": {"OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "unset")},
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": {
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "scipy": scipy.__version__,
            },
        },
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "duration_seconds": duration_seconds,
        "code": {"runner": "code/q3/full_audit_core.py", "sha256": sha256_file(SCRIPT)},
        "methods": [
            {
                "role": "main",
                "name": "regional full-horizon binary MILP audit probe",
                "implementation": "code/q3/full_audit_core.py",
                "output_class": "regional hourly storage dispatch and hard-constraint audit",
                "claim_eligible_scope": "feasibility and audit completeness only",
            },
            {
                "role": "baseline",
                "name": "deterministic no-storage renewable-first policy",
                "implementation": "code/q3/storage_core.py",
                "output_class": "regional hourly dispatch and the same hard-constraint audit",
                "comparable_output": True,
            },
        ],
        "artifacts": artifacts,
        "metrics": {
            "audits_passed": {"value": passed_count, "unit": "audit"},
            "audits_total": {"value": len(complete_audits), "unit": "audit"},
            "maximum_simultaneous_charge_discharge": {
                "value": max_simultaneous,
                "unit": "MW",
            },
            "maximum_mip_gap": {"value": max_gap, "unit": "ratio"},
        },
        "inputs": pinned_inputs,
        "status": "PASS",
        "outputs": CORE_OUTPUTS + ["run_manifest.json", "result_hashes.json"],
    }
    dump_json(output_dir / "run_manifest.json", manifest)
    hashes = {
        "schema_version": 1,
        "run_id": "q3-full-audit-fix-20260809",
        "core_outputs": {
            name: {
                "sha256": sha256_file(output_dir / name),
                "bytes": (output_dir / name).stat().st_size,
            }
            for name in CORE_OUTPUTS
        },
        "run_manifest": {
            "sha256": sha256_file(output_dir / "run_manifest.json"),
            "bytes": (output_dir / "run_manifest.json").stat().st_size,
        },
    }
    dump_json(output_dir / "result_hashes.json", hashes)
    return 0


def verify_replay(primary_dir: Path, replay_dir: Path) -> int:
    records: list[dict[str, Any]] = []
    for name in CORE_OUTPUTS:
        primary_path = primary_dir / name
        replay_path = replay_dir / name
        if not primary_path.is_file() or not replay_path.is_file():
            raise FileNotFoundError(f"missing replay comparison output: {name}")
        primary_hash = sha256_file(primary_path)
        replay_hash = sha256_file(replay_path)
        records.append(
            {
                "path": name,
                "primary_sha256": primary_hash,
                "replay_sha256": replay_hash,
                "match": primary_hash == replay_hash,
            }
        )

    primary_summary = load_json(primary_dir / "summary.json")
    replay_summary = load_json(replay_dir / "summary.json")
    primary_manifest = load_json(primary_dir / "run_manifest.json")
    replay_manifest = load_json(replay_dir / "run_manifest.json")
    stable_manifest_fields = ("random_seed", "engine", "environment", "code", "methods")
    stable_manifest_match = all(
        primary_manifest.get(key) == replay_manifest.get(key) for key in stable_manifest_fields
    )
    all_hashes_match = all(row["match"] for row in records)
    both_complete = all(
        summary.get("audit_boundary", {}).get("total_audits_passed")
        == summary.get("audit_boundary", {}).get("total_audit_count")
        == EXPECTED_TOTAL_AUDITS
        for summary in (primary_summary, replay_summary)
    )
    report = {
        "schema_version": 1,
        "run_id": "q3-full-audit-fix-20260809",
        "question_id": "Q3",
        "primary_directory": relative(primary_dir),
        "replay_directory": relative(replay_dir),
        "core_output_count": len(records),
        "core_outputs": records,
        "all_core_hashes_match": all_hashes_match,
        "stable_manifest_fields_match": stable_manifest_match,
        "primary_and_replay_are_270_of_270": both_complete,
        "passed": bool(all_hashes_match and stable_manifest_match and both_complete),
        "note": (
            "Run-manifest timestamps, duration and output-directory command arguments are "
            "intentionally excluded from byte-for-byte comparison."
        ),
    }
    if not report["passed"]:
        raise AssertionError(f"deterministic replay verification failed: {report}")
    report_path = primary_dir / "replay_report.json"
    dump_json(report_path, report)
    hashes = load_json(primary_dir / "result_hashes.json")
    hashes["replay_report"] = {
        "sha256": sha256_file(report_path),
        "bytes": report_path.stat().st_size,
    }
    dump_json(primary_dir / "result_hashes.json", hashes)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Q3 corrected 270-item audit")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument(
        "--verify-replay-dir",
        default=None,
        help="Compare an existing replay directory with --output-dir and write replay_report.json.",
    )
    args = parser.parse_args(argv)
    output_dir = args.output_dir.resolve()
    if args.verify_replay_dir is not None:
        replay_candidate = Path(args.verify_replay_dir)
        replay_dir = (
            replay_candidate
            if replay_candidate.is_absolute()
            else output_dir / replay_candidate
        )
        return verify_replay(output_dir, replay_dir.resolve())
    return generate(args.input_dir.resolve(), output_dir, args.seed)


if __name__ == "__main__":
    raise SystemExit(main())
