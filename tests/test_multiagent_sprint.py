from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from src.workflow.competition_workflow import (
    changed_fingerprints,
    check_sprint,
    fingerprint_files,
    initialize,
    merge_sprint,
    prepare_sprint,
)


ROOT = Path(__file__).resolve().parents[1]


def test_workspace_uri_fingerprint_uses_shared_root(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    workbench_root = tmp_path / "workbench"
    project_root.mkdir()
    workbench_root.mkdir()
    shared = workbench_root / "config" / "figure_style.yaml"
    shared.parent.mkdir()
    shared.write_text("palette_id: journal-spectrum-v2\n", encoding="utf-8")

    records = fingerprint_files(project_root, ["workspace://config/figure_style.yaml"], workbench_root)
    assert records[0]["path"] == "workspace://config/figure_style.yaml"
    assert records[0]["kind"] == "file"
    assert changed_fingerprints(project_root, records, workbench_root) == []

    shared.write_text("palette_id: changed\n", encoding="utf-8")
    assert changed_fingerprints(project_root, records, workbench_root) == [
        "workspace://config/figure_style.yaml"
    ]


def scaffold(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir()
    (root / "paper").mkdir()
    (root / "contest.yaml").write_text(
        "competition: CUMCM\nyear: 2026\nproblem: TBD\ndeadline: '2026-09-13T20:00:00+08:00'\n",
        encoding="utf-8",
    )
    for name in ("config/workflow.yaml", "skills.lock.yaml"):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        source = ROOT / name
        shutil.copy2(source, target)
    template = root / "templates/workflow/question.yaml"
    template.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "templates/workflow/question.yaml", template)
    decision = root / "skill_staging/handsomeZR-mathmodel-skill/templates/shared/decision_log.json"
    decision.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "skill_staging/handsomeZR-mathmodel-skill/templates/shared/decision_log.json", decision)


def make_active(root: Path, questions: int = 2) -> None:
    source = root / "problems/problem.txt"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("\n".join(f"问题{i} 建立可验证模型。" for i in range(1, questions + 1)), encoding="utf-8")
    initialize(root, "C", source)


def write_handoff(root: Path, task: dict, status: str = "SUCCESS", outside: bool = False) -> None:
    write_dir = root / task["write_directory"]
    write_dir.mkdir(parents=True, exist_ok=True)
    artifact_paths: list[Path] = []
    for value in task["expected_outputs"]:
        target = root / value
        if target.name == "handoff.json":
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"task": task["task_id"], "artifact": target.name}), encoding="utf-8")
        artifact_paths.append(target)
    if not artifact_paths:
        artifact_path = write_dir / "result.json"
        artifact_path.write_text(json.dumps({"task": task["task_id"], "score": 1.0}), encoding="utf-8")
        artifact_paths.append(artifact_path)
    if outside:
        written_paths = ["paper/main.tex"]
        artifact_records = [{"path": "paper/main.tex", "sha256": "0" * 64}]
    else:
        written_paths = [path.relative_to(root).as_posix() for path in artifact_paths]
        artifact_records = [
            {"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in artifact_paths
        ]
    handoff = {
        "schema_version": 1,
        "sprint_id": task["sprint_id"],
        "task_id": task["task_id"],
        "attempt": task["attempt"],
        "status": status,
        "input_hashes": task["input_hashes"],
        "written_paths": written_paths,
        "artifacts": artifact_records,
        "gate_result": {"gate": task["target_gate"], "passed": status == "SUCCESS", "checks": ["fixture"]},
        "summary": "fixture handoff",
    }
    (write_dir / "handoff.json").write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")


def read_tasks(root: Path, result: dict) -> list[dict]:
    return [json.loads((root / path).read_text(encoding="utf-8")) for path in result["task_files"]]


def test_sprint_is_explicit_and_forbidden_precontest(tmp_path: Path) -> None:
    scaffold(tmp_path)
    with pytest.raises(ValueError, match="TBD"):
        prepare_sprint(tmp_path, "parallel", 3)
    assert not (tmp_path / "state/decision_log.json").exists()
    assert not (tmp_path / "sprints").exists()
    with pytest.raises(ValueError, match="opt-in"):
        prepare_sprint(tmp_path, "off", 1, "C")


def test_prepare_scope_partial_retry_and_merge(tmp_path: Path) -> None:
    scaffold(tmp_path)
    make_active(tmp_path, 2)
    with pytest.raises(ValueError, match="between 1 and 3"):
        prepare_sprint(tmp_path, "parallel", 4)
    prepared = prepare_sprint(tmp_path, "parallel", 3)
    assert prepared["task_count"] == 2
    tasks = read_tasks(tmp_path, prepared)
    assert len({task["write_directory"] for task in tasks}) == 2
    write_handoff(tmp_path, tasks[0], "SUCCESS")
    write_handoff(tmp_path, tasks[1], "PARTIAL")

    checked = check_sprint(tmp_path, prepared["sprint_id"])
    assert checked["status"] == "PARTIAL"
    assert checked["accepted_tasks"] == [tasks[0]["task_id"]]
    merged = merge_sprint(tmp_path, prepared["sprint_id"])
    assert merged["status"] == "PARTIAL"
    assert len(merged["archived_artifacts"]) == 1
    assert len(merged["retry_packages"]) == 1
    assert merged["formal_state_modified"] is False

    retry_task_path = tmp_path / merged["retry_packages"][0]
    retry_task = json.loads(retry_task_path.read_text(encoding="utf-8"))
    write_handoff(tmp_path, retry_task, "SUCCESS")
    checked_again = check_sprint(tmp_path, prepared["sprint_id"])
    assert checked_again["status"] == "READY_TO_MERGE"
    merged_again = merge_sprint(tmp_path, prepared["sprint_id"])
    assert merged_again["passed"] is True
    assert (tmp_path / "sprints" / prepared["sprint_id"] / "merged").is_dir()
    assert not (tmp_path / "paper/main.tex").exists()


def test_stale_input_and_scope_violation_are_blocked(tmp_path: Path) -> None:
    scaffold(tmp_path)
    make_active(tmp_path, 1)
    prepared = prepare_sprint(tmp_path, "parallel", 1)
    task = read_tasks(tmp_path, prepared)[0]
    question = tmp_path / f"problems/C/questions/{task['question']}/question.yaml"
    question.write_text(question.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    write_handoff(tmp_path, task, "SUCCESS")
    stale = check_sprint(tmp_path, prepared["sprint_id"])
    assert stale["status"] == "BLOCKED"
    assert any(issue["kind"] == "stale_input" for issue in stale["tasks"][0]["issues"])

    # A fresh sprint isolates the scope check from the stale-input check.
    question.write_text(question.read_text(encoding="utf-8").replace("\n# changed\n", "\n"), encoding="utf-8")
    prepared = prepare_sprint(tmp_path, "parallel", 1)
    task = read_tasks(tmp_path, prepared)[0]
    write_handoff(tmp_path, task, "SUCCESS", outside=True)
    blocked = check_sprint(tmp_path, prepared["sprint_id"])
    assert blocked["status"] == "BLOCKED"
    assert any(issue["kind"] == "scope_violation" for issue in blocked["tasks"][0]["issues"])


def test_q1_solve_profile_creates_two_scoped_workers(tmp_path: Path) -> None:
    scaffold(tmp_path)
    make_active(tmp_path, 1)
    data_dir = tmp_path / "problems/C/data"
    data_dir.mkdir(parents=True)
    for name in ("workload_trace.xlsx", "GPU_information.xlsx", "network_latency.xlsx", "region_time_data.xlsx", "power_mapping.xlsx"):
        (data_dir / name).write_text(name, encoding="utf-8")

    prepared = prepare_sprint(tmp_path, "parallel", 2, "C", question="Q1", sprint_profile="q1-solve")
    tasks = read_tasks(tmp_path, prepared)
    assert prepared["task_count"] == 2
    assert {task["task_id"] for task in tasks} == {"forecast-q1", "scheduling-q1"}
    assert {task["role"] for task in tasks} == {"solver"}
    assert all(task["question"] == "Q1" for task in tasks)
    assert all(task["sprint_profile"] == "q1-solve" for task in tasks)
    assert len({task["write_directory"] for task in tasks}) == 2
    forecast = next(task for task in tasks if task["task_id"] == "forecast-q1")
    scheduling = next(task for task in tasks if task["task_id"] == "scheduling-q1")
    assert any(path.endswith("/metrics_summary.json") for path in forecast["expected_outputs"])
    assert any(path.endswith("/constraint_audit.json") for path in scheduling["expected_outputs"])
    assert any(path.endswith("/carry_in.json") for path in scheduling["expected_outputs"])


def test_q1_solve_missing_required_evidence_is_retried(tmp_path: Path) -> None:
    scaffold(tmp_path)
    make_active(tmp_path, 1)
    data_dir = tmp_path / "problems/C/data"
    data_dir.mkdir(parents=True)
    for name in ("workload_trace.xlsx", "GPU_information.xlsx", "network_latency.xlsx", "region_time_data.xlsx", "power_mapping.xlsx"):
        (data_dir / name).write_text(name, encoding="utf-8")

    prepared = prepare_sprint(tmp_path, "parallel", 2, "C", question="Q1", sprint_profile="q1-solve")
    tasks = read_tasks(tmp_path, prepared)
    for task in tasks:
        write_handoff(tmp_path, task, "SUCCESS")
    forecast = next(task for task in tasks if task["task_id"] == "forecast-q1")
    missing = next(path for path in forecast["expected_outputs"] if path.endswith("/metrics_summary.json"))
    (tmp_path / missing).unlink()

    checked = check_sprint(tmp_path, prepared["sprint_id"])
    report = next(item for item in checked["tasks"] if item["task_id"] == "forecast-q1")
    assert report["disposition"] == "RETRY_REQUIRED"
    assert any(issue["kind"] == "missing_expected_output" for issue in report["issues"])


def test_q1_compose_requires_merged_q1_solve_and_pins_hashes(tmp_path: Path) -> None:
    scaffold(tmp_path)
    make_active(tmp_path, 1)
    data_dir = tmp_path / "problems/C/data"
    data_dir.mkdir(parents=True)
    for name in ("workload_trace.xlsx", "GPU_information.xlsx", "network_latency.xlsx", "region_time_data.xlsx", "power_mapping.xlsx"):
        (data_dir / name).write_text(name, encoding="utf-8")
    solve = prepare_sprint(tmp_path, "parallel", 2, "C", question="Q1", sprint_profile="q1-solve")
    for task in read_tasks(tmp_path, solve):
        write_handoff(tmp_path, task, "SUCCESS")
    assert merge_sprint(tmp_path, solve["sprint_id"])["passed"] is True

    compose = prepare_sprint(
        tmp_path,
        "parallel",
        2,
        "C",
        question="Q1",
        sprint_profile="q1-compose",
        input_sprint_id=solve["sprint_id"],
    )
    tasks = read_tasks(tmp_path, compose)
    assert {task["task_id"] for task in tasks} == {"writer-q1", "reviewer-q1"}
    assert {task["role"] for task in tasks} == {"writer", "reviewer"}
    assert all(task["target_gate"] == "G5" for task in tasks)
    assert all(task["input_sprint_id"] == solve["sprint_id"] for task in tasks)

    merged_dir = tmp_path / "sprints" / solve["sprint_id"] / "merged"
    marker = merged_dir / "forecast-q1" / "run_manifest.json"
    marker.write_text(marker.read_text(encoding="utf-8") + "\nchanged", encoding="utf-8")
    assert check_sprint(tmp_path, compose["sprint_id"])["status"] == "BLOCKED"
