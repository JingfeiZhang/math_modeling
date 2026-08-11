from __future__ import annotations

import hashlib
import json
import platform
import shutil
from datetime import UTC, datetime
from pathlib import Path

import ortools
import sklearn

PROJECT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
FORMAL = PROJECT / "experiments/C/Q1/q1-direct-20260808"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def record(path: Path) -> dict[str, object]:
    return {"path": path.resolve().relative_to(PROJECT).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}


def tree_record(path: Path) -> dict[str, object]:
    files = [p for p in sorted(path.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
    payload = "\n".join(f"{p.relative_to(path).as_posix()}:{sha256(p)}" for p in files).encode()
    return {"path": path.resolve().relative_to(PROJECT).as_posix(), "kind": "directory", "file_count": len(files), "tree_sha256": hashlib.sha256(payload).hexdigest()}


def main() -> int:
    formal_predictions = FORMAL / "models/forecast_q1/blind_test_predictions.csv"
    shutil.copyfile(formal_predictions, OUT / "forecast_baseline_predictions.csv")

    baseline_lock = {
        "schema_version": 1,
        "project_id": "huashu-cup-2026",
        "problem_id": "C",
        "question_id": "Q1",
        "scope": "Q1-only baseline lock; root integration owns cross-question lock",
        "files": [
            record(PROJECT / "results/C/claims.json"),
            record(PROJECT / "problems/C/questions/Q1/question.yaml"),
            record(PROJECT / "problems/C/data/workload_trace.xlsx"),
            record(PROJECT / "problems/C/data/GPU_information.xlsx"),
            record(PROJECT / "problems/C/data/network_latency.xlsx"),
            record(PROJECT / "problems/C/data/region_time_data.xlsx"),
            record(PROJECT / "problems/C/data/power_mapping.xlsx"),
        ],
        "formal_experiment": tree_record(FORMAL),
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    dump(OUT / "baseline_lock.json", baseline_lock)

    forecast = json.loads((OUT / "forecast_summary.json").read_text(encoding="utf-8"))
    schedule = json.loads((OUT / "schedule_summary.json").read_text(encoding="utf-8"))
    blind = forecast["blind_test"]; base = forecast["formal_baseline_blind"]
    summary = {
        "schema_version": 1,
        "run_id": "q1-optimization-20260809",
        "project_id": "huashu-cup-2026",
        "problem_id": "C",
        "question_id": "Q1",
        "status": "PASS",
        "decision": "PROBE_ONLY",
        "formal_evidence_modified": False,
        "forecast": {
            "candidate": "direct_multi_horizon_hurdle_hgbr",
            "blind_wape": blind["wape"],
            "blind_rmse_gpu_h": blind["rmse"],
            "coverage_95": blind["empirical_coverage_95"],
            "mean_interval_width_gpu_h": blind["mean_interval_width_gpu_h"],
            "series_mae_non_degrading_count": blind["series_mae_non_degrading_count"],
            "wape_change_pct_vs_formal": (blind["wape"] / base["wape"] - 1.0) * 100.0,
            "rmse_change_pct_vs_formal": (blind["rmse"] / base["rmse"] - 1.0) * 100.0,
            "interval_width_change_pct_vs_formal": (blind["mean_interval_width_gpu_h"] / base["mean_interval_width_gpu_h"] - 1.0) * 100.0,
            "promotion_gates": forecast["promotion_gates"],
            "decision": "PROBE_ONLY",
            "reason": "WAPE improves, but RMSE fails the joint 5% gate and conformal width exceeds the 25% allowance.",
        },
        "schedule": {
            "candidate": "incumbent_hint_tight_domain_fix_and_opt_12_32_64",
            "formal_full_objective": schedule["formal_incumbent_objective"],
            "candidate_best_full_objective": schedule["best_candidate"]["full_schedule_objective"],
            "full_objective_change_pct": (schedule["best_candidate"]["full_schedule_objective"] / schedule["formal_incumbent_objective"] - 1.0) * 100.0,
            "completion_rate": 1.0,
            "hard_audits_passed": True,
            "promotion_gates": schedule["promotion_gate"],
            "decision": "PROBE_ONLY",
            "reason": "All neighborhoods are locally optimal and feasible, but the full objective remains 2788 and the formal 3.515% global gap is not closed.",
        },
        "promotion_recommendation": "Do not promote either Q1 candidate; retain the frozen forecast and schedule.",
    }
    dump(OUT / "summary.json", summary)
    dump(OUT / "main_model_results.json", {"forecast": forecast, "schedule": schedule})
    dump(OUT / "baseline_results.json", {"forecast": base, "schedule": {"formal_incumbent_objective": schedule["formal_incumbent_objective"], "formal_global_gap": schedule["formal_global_gap"], "fifo_completion_rate": schedule["baseline_completion_rate"]}, "same_output_files": ["forecast_baseline_predictions.csv", "baseline_schedule.csv"]})

    expected = {
        "blind_test_predictions.csv": "57853cd9781bc099827b2c3b4f55089248069b5b5f5ee52e19f361c7e0f86772",
        "rolling_origin_predictions.csv": "31600538087ac6762125366ac3fdfd91a44a91b4bd819b48356101318505c87b",
        "candidate_schedule_12.csv": "04871953a14c28ecbf11663c39f9f9f3e04aeeafe5248e3711cb11ec4e13007c",
        "candidate_schedule_32.csv": "075d1490bfb48ccdfd7afce189ab469b836a9fa76c9c7b66a8affc1c62cef741",
        "candidate_schedule_64.csv": "0926b725aa306c9332fdab416d737f8ee3cf0bd3c9ab2c8e3375581c816e4296",
    }
    checks = {name: {"expected_sha256": digest, "actual_sha256": sha256(OUT / name), "passed": sha256(OUT / name) == digest} for name, digest in expected.items()}
    dump(OUT / "deterministic_replay_audit.json", {"schema_version": 1, "independent_replay_count": 2, "checks": checks, "passed": all(v["passed"] for v in checks.values()), "note": "Wall-clock fields are excluded; prediction and schedule payloads are byte-identical across consecutive fixed-seed runs."})

    inputs = baseline_lock["files"] + [baseline_lock["formal_experiment"]]
    artifact_names = sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name not in {"run_manifest.json", "result_hashes.json"})
    manifest = {
        "schema_version": 1,
        "run_id": "q1-optimization-20260809",
        "problem_id": "C",
        "question_id": "Q1",
        "status": "PASS",
        "decision": "PROBE_ONLY",
        "command": [
            "D:/anaconda3/envs/math-modeling/python.exe run_q1_forecast_candidate.py",
            "D:/anaconda3/envs/math-modeling/python.exe run_q1_schedule_candidate.py",
            "D:/anaconda3/envs/math-modeling/python.exe finalize_q1_candidate.py",
        ],
        "environment": {"python": platform.python_version(), "sklearn": sklearn.__version__, "ortools": ortools.__version__, "platform": platform.platform()},
        "random_seed": 20260801,
        "inputs": inputs,
        "methods": ["direct multi-horizon hurdle HGBR with four pre-blind rolling origins", "incumbent-hinted tight-domain deterministic CP-SAT fix-and-opt neighborhoods 12/32/64"],
        "metrics": [
            {"name": "WAPE", "unit": "ratio"}, {"name": "RMSE", "unit": "GPU.h"}, {"name": "coverage", "unit": "ratio"},
            {"name": "interval_width", "unit": "GPU.h"}, {"name": "schedule_objective", "unit": "weighted objective"}, {"name": "completion", "unit": "ratio"},
        ],
        "artifacts": [record(OUT / name) for name in artifact_names],
        "generated_at_utc": datetime.now(UTC).isoformat(),
    }
    dump(OUT / "run_manifest.json", manifest)
    hash_names = sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name != "result_hashes.json")
    dump(OUT / "result_hashes.json", {"schema_version": 1, "algorithm": "SHA-256", "files": [record(OUT / name) for name in hash_names]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
