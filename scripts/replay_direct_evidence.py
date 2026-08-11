"""Sequentially replay stable compatibility evidence for C/Q1--Q4."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = WORKSPACE_ROOT / "projects" / "huashu-cup" / "2026"

RUNS = {
    "Q1": {
        "generator": PROJECT_ROOT / "experiments/C/Q1/q1-derived-20260807/generate_q1_derived.py",
        "stable": ["q1_derived_summary.json", "claim_proposals.json"],
        "direct": PROJECT_ROOT / "experiments/C/Q1/q1-direct-20260808",
    },
    "Q2": {
        "generator": PROJECT_ROOT / "experiments/C/Q2/q2-full-compat-20260808/generate_q2_compat.py",
        "stable": [
            "q2_compat_summary.json",
            "claim_proposals.json",
            "q2_renewable_accounting.csv",
            "q2_renewable_metric_audit.json",
            "risk_probes.json",
            "result_hashes.json",
        ],
        "direct": PROJECT_ROOT / "experiments/C/Q2/q2-direct-20260808",
    },
    "Q3": {
        "generator": PROJECT_ROOT / "experiments/C/Q3/q3-rolling-compat-20260808/generate_q3_compat.py",
        "stable": ["q3_derived_summary.json", "claim_proposals.json"],
        "direct": PROJECT_ROOT / "experiments/C/Q3/q3-direct-20260808",
    },
    "Q4": {
        "generator": PROJECT_ROOT / "experiments/C/Q4/q4-integrated-compat-20260808/generate_q4_compat.py",
        "stable": ["q4_derived_summary.json", "claim_proposals.json"],
        "direct": PROJECT_ROOT / "experiments/C/Q4/q4-direct-20260808",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_once(generator: Path) -> tuple[int, str, str]:
    completed = subprocess.run(
        [sys.executable, "-s", str(generator)],
        cwd=WORKSPACE_ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def main() -> None:
    for question, config in RUNS.items():
        generator = config["generator"]
        direct = config["direct"]
        if not generator.is_file() or not direct.is_dir():
            raise FileNotFoundError(f"missing direct replay input for {question}")
        first_code, first_stdout, first_stderr = run_once(generator)
        if first_code != 0:
            raise RuntimeError(f"{question} first replay failed: {first_stderr or first_stdout}")
        stable_paths = [generator.parent / name for name in config["stable"]]
        first_hashes = {relative(path): sha256(path) for path in stable_paths}
        second_code, second_stdout, second_stderr = run_once(generator)
        if second_code != 0:
            raise RuntimeError(f"{question} second replay failed: {second_stderr or second_stdout}")
        second_hashes = {relative(path): sha256(path) for path in stable_paths}
        passed = first_hashes == second_hashes
        audit = {
            "schema_version": 1,
            "problem_id": "C",
            "question_id": question,
            "status": "PASS" if passed else "FAIL",
            "generator": {"path": relative(generator), "sha256": sha256(generator)},
            "command": [sys.executable, "-s", relative(generator)],
            "replay_count": 2,
            "stable_artifacts": [
                {"path": path, "first_sha256": digest, "second_sha256": second_hashes[path]}
                for path, digest in first_hashes.items()
            ],
            "stable_output_hashes_identical": passed,
            "runtime_metadata_excluded": ["started_at_utc", "duration_seconds"],
            "generated_at_utc": datetime.now(UTC).isoformat(),
        }
        audit_path = direct / "deterministic_replay_audit.json"
        write_json(audit_path, audit)
        if not passed:
            raise RuntimeError(f"{question} stable replay artifacts changed")

        hashes_path = direct / "result_hashes.json"
        hashes = json.loads(hashes_path.read_text(encoding="utf-8"))
        audit_record = {"path": relative(audit_path), "sha256": sha256(audit_path)}
        hashes["files"] = [item for item in hashes["files"] if item["path"] != audit_record["path"]]
        hashes["files"].append(audit_record)
        write_json(hashes_path, hashes)

        manifest_path = direct / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["deterministic_replay"] = audit_record | {"passed": True, "count": 2}
        manifest["result_hashes"] = {"path": relative(hashes_path), "sha256": sha256(hashes_path)}
        write_json(manifest_path, manifest)


if __name__ == "__main__":
    main()
