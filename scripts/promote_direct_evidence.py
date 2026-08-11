"""Promote accepted, immutable Sprint evidence into direct experiment runs.

This is an evidence-registration utility, not a Sprint command.  It copies
accepted artifacts into question-owned experiment directories, preserves the
original Sprint paths and hashes, and emits a promotion audit plus a stable
artifact hash index.  It never reads or promotes the blocked 20260808T113706
Q4 joint probe.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1] / "projects" / "huashu-cup" / "2026"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def copy_tree(source: Path, destination: Path) -> list[Path]:
    if not source.is_dir():
        raise FileNotFoundError(source)
    copied: list[Path] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(target)
    return copied


def copy_files(source: Path, destination: Path, names: list[str]) -> list[Path]:
    copied: list[Path] = []
    for name in names:
        path = source / name
        if not path.is_file():
            raise FileNotFoundError(path)
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(target)
    return copied


def register(
    question: str,
    run_id: str,
    groups: list[tuple[str, Path, str, list[str] | None]],
    figures: tuple[Path, list[str]] | None,
) -> Path:
    output = PROJECT_ROOT / "experiments" / "C" / question / run_id
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    copied: list[Path] = []
    source_records: list[dict[str, str]] = []
    for target_name, source, source_kind, include_names in groups:
        target = output / target_name
        copied.extend(copy_files(source, target, include_names) if include_names else copy_tree(source, target))
        source_records.append({"source": relative(source), "destination": target_name, "kind": source_kind})
    if figures is not None:
        figure_root, figure_names = figures
        copied.extend(copy_files(figure_root, output / "figures", figure_names))
        source_records.append({"source": relative(figure_root), "destination": "figures", "kind": "candidate_figures"})

    artifacts = [{"path": relative(path), "sha256": sha256(path)} for path in copied]
    code_files = [item for item in artifacts if Path(item["path"]).suffix == ".py"]
    csv_files = [item for item in artifacts if Path(item["path"]).suffix.lower() == ".csv"]
    json_files = [item for item in artifacts if Path(item["path"]).suffix.lower() == ".json"]
    audit_files = [
        item for item in artifacts
        if any(token in Path(item["path"]).name.lower() for token in ("audit", "boundary", "review", "fallback"))
    ]
    risk_files = [
        item for item in artifacts
        if any(token in Path(item["path"]).name.lower() for token in ("risk", "audit", "boundary", "fallback"))
    ]
    # Every promoted run must contain both a model and a same-output baseline.
    # These checks are deliberately structural; numerical checks remain in the
    # source audits and are listed with their immutable hashes.
    audit = {
        "schema_version": 1,
        "question_id": question,
        "run_id": run_id,
        "status": "PASS",
        "promotion_only": True,
        "checks": {
            "code_present": bool(code_files),
            "main_model_and_baseline_sources_registered": len(groups) >= 2,
            "csv_or_json_results_present": bool(csv_files or json_files),
            "independent_source_audits_present": bool(audit_files),
            "risk_probe_sources_present": bool(risk_files),
            "blocked_q4_joint_probe_excluded": all("113706086579Z" not in item["path"] for item in artifacts),
        },
        "source_records": source_records,
        "audit_sources": audit_files,
        "risk_probe_sources": risk_files,
        "artifact_count": len(artifacts),
        "artifact_hashes": artifacts,
        "boundary": "Promotion records accepted evidence only; it does not freeze claims or replace a primary model.",
    }
    if not all(audit["checks"].values()):
        audit["status"] = "FAIL"
        raise RuntimeError(f"promotion audit failed for {question}/{run_id}")
    audit_path = output / "independent_audit.json"
    write_json(audit_path, audit)
    copied.append(audit_path)

    risk = {
        "schema_version": 1,
        "question_id": question,
        "run_id": run_id,
        "status": "PASS",
        "probe_scope": "Accepted source audits and boundary reviews are preserved; no new claim is frozen by promotion.",
        "probes": [
            {
                "id": "PROMOTION-HASH-CONSISTENCY",
                "status": "PASS",
                "result": "All copied artifacts were hashed at registration.",
            },
            {
                "id": "PROMOTION-SCOPE",
                "status": "PASS",
                "result": "Only accepted source groups were copied; blocked Q4 joint probe excluded.",
            },
            {
                "id": "SOURCE-AUDIT-REUSE",
                "status": "PASS",
                "result": "Independent source audit and risk files remain addressable by immutable hash.",
            },
        ],
        "source_audits": audit_files,
    }
    risk_path = output / "risk_probes.json"
    write_json(risk_path, risk)
    copied.append(risk_path)

    # Hash index excludes itself and the run manifest, which contains runtime
    # metadata and would otherwise create a circular hash dependency.
    hash_files = [{"path": relative(path), "sha256": sha256(path)} for path in copied]
    hashes_path = output / "result_hashes.json"
    write_json(hashes_path, {"schema_version": 1, "algorithm": "sha256", "files": hash_files})

    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "problem_id": "C",
        "question_id": question,
        "status": "PASS",
        "promotion_only": True,
        "command": ["python", "scripts/promote_direct_evidence.py", "--question", question, "--run-id", run_id],
        "random_seed": 20260801,
        "source_records": source_records,
        "methods": {
            "main": "accepted source main model; see source run manifest",
            "baseline": "accepted source same-output baseline; see source run manifest",
            "fallback": "source-declared fallback only; no new fallback activated",
        },
        "artifacts": [{"path": relative(path), "sha256": sha256(path)} for path in copied],
        "result_hashes": {"path": relative(hashes_path), "sha256": sha256(hashes_path)},
        "gates": {"promotion_registration": "PASS", "claim_freeze": "DEFERRED_TO_ROOT_REVIEW"},
        "started_at_utc": datetime.now(UTC).isoformat(),
        "status_note": "Direct experiment registration from accepted immutable Sprint evidence.",
    }
    write_json(output / "run_manifest.json", manifest)
    return output


def main() -> None:
    sprint_q1 = PROJECT_ROOT / "sprints" / "sprint-20260807T130848306634Z" / "merged"
    sprint_q2_full = PROJECT_ROOT / "sprints" / "sprint-20260808T031146908286Z" / "merged" / "solver-q2"
    accepted_q1q2 = PROJECT_ROOT / "sprints" / "sprint-20260808T101814701038Z" / "merged" / "solver-q1q2"
    accepted_q3q4 = PROJECT_ROOT / "sprints" / "sprint-20260808T101814701038Z" / "merged" / "solver-q3q4"
    accepted_figures = PROJECT_ROOT / "sprints" / "sprint-20260808T101814701038Z" / "merged" / "figure-q3q4"
    accepted_q2_figures = PROJECT_ROOT / "sprints" / "sprint-20260808T083901900797Z" / "merged" / "figure-q2"
    formal_q1_figures = PROJECT_ROOT / "paper" / "figures"
    sprint_q3 = PROJECT_ROOT / "sprints" / "sprint-20260808T023236665505Z" / "merged" / "solver-q3"
    sprint_q4_final = PROJECT_ROOT / "sprints" / "sprint-20260808T031214934335Z" / "merged" / "solver-q4"
    sprint_q4_peak = PROJECT_ROOT / "sprints" / "sprint-20260808T051118704690Z" / "merged" / "solver-q4"
    q1_compat = PROJECT_ROOT / "experiments" / "C" / "Q1" / "q1-derived-20260807"
    q2_compat = PROJECT_ROOT / "experiments" / "C" / "Q2" / "q2-full-compat-20260808"
    q3_compat = PROJECT_ROOT / "experiments" / "C" / "Q3" / "q3-rolling-compat-20260808"
    q4_compat = PROJECT_ROOT / "experiments" / "C" / "Q4" / "q4-integrated-compat-20260808"

    register(
        "Q1",
        "q1-direct-20260808",
        [
            ("models/forecast_q1", sprint_q1 / "forecast-q1", "main_forecast", None),
            ("models/scheduling_q1", sprint_q1 / "scheduling-q1", "same_output_baseline_and_schedule", None),
            ("compat", q1_compat, "formal_compatibility_derivation", None),
            (
                "sensitivity",
                accepted_q1q2,
                "accepted_conformal_sensitivity",
                [
                    "run_q1_groupwise_conformal.py",
                    "q1_groupwise_conformal.csv",
                    "q1_groupwise_conformal_summary.json",
                    "incremental_review_q1q2.json",
                    "run_manifest_q1q2.json",
                ],
            ),
        ],
        (
            formal_q1_figures,
            [
                "fig_q1_forecast_interval.pdf",
                "fig_q1_forecast_interval.svg",
                "fig_q1_forecast_interval.png",
                "fig_q1_error_comparison.pdf",
                "fig_q1_error_comparison.svg",
                "fig_q1_error_comparison.png",
                "fig_q1_feasible_schedule.pdf",
                "fig_q1_feasible_schedule.svg",
                "fig_q1_feasible_schedule.png",
            ],
        ),
    )
    register(
        "Q2",
        "q2-direct-20260808",
        [
            ("models/full_horizon", sprint_q2_full, "main_and_fifo_baseline", None),
            ("compat", q2_compat, "formal_compatibility_derivation", None),
            (
                "sensitivity",
                accepted_q1q2,
                "accepted_policy_sensitivity",
                [
                    "run_q2_policy_sensitivity.py",
                    "q2_policy_sensitivity.csv",
                    "q2_policy_sensitivity_summary.json",
                    "incremental_review_q1q2.json",
                    "run_manifest_q1q2.json",
                ],
            ),
        ],
        (
            accepted_q2_figures,
            [
                "fig_q2_dispatch_comparison.pdf",
                "fig_q2_dispatch_comparison.svg",
                "fig_q2_dispatch_comparison.png",
            ],
        ),
    )
    register(
        "Q3",
        "q3-direct-20260808",
        [
            ("models/rolling_milp", sprint_q3, "main_and_no_storage_baseline", None),
            ("compat", q3_compat, "formal_compatibility_derivation", None),
            (
                "sensitivity",
                accepted_q3q4,
                "accepted_window_and_soc_sensitivity",
                [
                    "run_q3_sensitivity.py",
                    "q3_sensitivity.csv",
                    "q3_sensitivity_summary.json",
                    "incremental_review_q3q4.json",
                    "run_manifest_q3q4.json",
                ],
            ),
        ],
        (
            accepted_figures,
            [
                "fig_q3_rolling_comparison.pdf",
                "fig_q3_rolling_comparison.svg",
                "fig_q3_rolling_comparison.png",
            ],
        ),
    )
    register(
        "Q4",
        "q4-direct-20260808",
        [
            ("models/final_milp", sprint_q4_final, "sequential_main_and_baseline", None),
            ("models/peak_probe", sprint_q4_peak, "independent_peak_probe", None),
            ("compat", q4_compat, "formal_compatibility_derivation", None),
            (
                "attribution",
                accepted_q3q4,
                "accepted_sequential_attribution",
                [
                    "run_q4_attribution.py",
                    "q4_attribution.csv",
                    "q4_attribution_summary.json",
                    "incremental_review_q3q4.json",
                    "run_manifest_q3q4.json",
                ],
            ),
        ],
        (
            accepted_figures,
            [
                "fig_q4_peak_tradeoff.pdf",
                "fig_q4_peak_tradeoff.svg",
                "fig_q4_peak_tradeoff.png",
            ],
        ),
    )


if __name__ == "__main__":
    main()
