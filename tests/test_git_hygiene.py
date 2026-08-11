from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def git_check_ignore(path: str) -> bool:
    completed = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", path],
        cwd=ROOT,
        check=False,
    )
    return completed.returncode == 0


def test_transient_workflow_artifacts_are_ignored() -> None:
    for path in (
        "tmp/work.txt",
        ".audit/render.png",
        ".tools/runtime/pyvenv.cfg",
        "output/.conda-tmp/call/state.json",
        "output/_verification/previews/Q1.pdf",
        "output/_package_staging/supporting.zip",
        "projects/demo/2026/paper/staging/preview.pdf",
        "projects/demo/2026/paper/.preview-worktree/main.tex",
        "projects/demo/2026/paper/.preview-build/main.pdf",
        "projects/demo/2026/output/.support-staging/package.zip",
        "projects/demo/2026/output/_verification/figures/qa.json",
        "projects/demo/2026/output/_archive/scratch/run-1.zip",
        "projects/demo/2026/output/_preview/Q1.pdf",
        "projects/demo/2026/output/_package_staging/supporting.zip",
        "projects/demo/2026/output/package_audit_staging.json",
        "projects/demo/2026/sprints/sprint-1/staging/worker/handoff.json",
        "projects/demo/2026/sprints/sprint-1/retry-staging/worker/handoff.json",
        "experiments/C/Q1/scratch/run-1/run_manifest.json",
        "experiments/C/Q1/formal/run-1/figure-staging/fig-q1/outputs/fig-q1.png",
        "experiments/C/Q1/candidate/run-1/artifacts/large.csv",
        "projects/demo/2026/experiments/C/Q1/scratch/run-1/probe_receipt.json",
        "projects/demo/2026/experiments/C/Q1/formal/run-1/figure-staging/fig-q1/figure_qa.json",
        "projects/demo/2026/experiments/C/Q1/candidate/run-1/outputs/preview.csv",
    ):
        assert git_check_ignore(path), path


def test_formal_evidence_and_sources_remain_trackable() -> None:
    for path in (
        "src/workflow/competition_workflow.py",
        "templates/workflow/experiment.yaml",
        "paper/sections/question_1.tex",
        "experiments/C/Q1/formal/run-1/run_manifest.json",
        "experiments/C/Q1/paper-evidence/run-1/paper_evidence_manifest.json",
    ):
        assert not git_check_ignore(path), path
