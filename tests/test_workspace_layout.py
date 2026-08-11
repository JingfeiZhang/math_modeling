from __future__ import annotations

import json
from pathlib import Path

from src.utils.workspace_layout import (
    inside,
    inspect,
    normalize,
    plan_payload,
    verify,
)


ROLE_DIRS = ("config", "templates", "corpus", "src", "scripts", "matlab", "projects", "paper", "problems", "experiments", "results", "figures", "reports", "tools", ".tools", ".audit", "skill_staging", "tmp", "output")


def make_workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workbench"
    for relative in ROLE_DIRS:
        (root / relative).mkdir(parents=True)
    project_root = root / "projects" / "huashu-cup" / "2026"
    (project_root / "state").mkdir(parents=True)
    (project_root / "paper").mkdir(parents=True)
    (project_root / "contest.yaml").write_text("problem: TBD\n", encoding="utf-8")
    (root / "contest.yaml").write_text("problem: TBD\n", encoding="utf-8")
    (root / "config" / "projects.json").write_text(json.dumps({"projects": [{"id": "huashu-cup-2026", "root": "projects/huashu-cup/2026"}]}), encoding="utf-8")
    return root


def test_inventory_and_preview_are_non_destructive(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    pytest_dir = root / "output" / "pytest-base"
    pytest_dir.mkdir(parents=True)
    (pytest_dir / "result.txt").write_text("pass\n", encoding="utf-8")
    pdf_pages = root / "output" / "pdf-visual-pages"
    pdf_pages.mkdir(parents=True)
    (pdf_pages / "page-1.png").write_bytes(b"png")
    before = (pytest_dir / "result.txt").read_bytes()

    report = inspect(root, root / "output" / "workspace_inventory.json")
    preview = plan_payload(root)

    assert report["roles"]["projects"]["projects"]["exists"] is True
    assert any(item["source"] == "output/pytest-base" for item in preview)
    assert any(item["source"] == "output/pdf-visual-pages" for item in preview)
    assert (pytest_dir / "result.txt").read_bytes() == before


def test_normalize_moves_only_allowlisted_artifacts_and_is_idempotent(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    source = root / "output" / "pytest-base"
    source.mkdir(parents=True)
    (source / "result.txt").write_text("pass\n", encoding="utf-8")
    (root / "projects" / "huashu-cup" / "2026" / "paper" / "keep.tex").write_text("keep\n", encoding="utf-8")

    first = normalize(root)
    target = root / "output" / "_verification" / "pytest" / "pytest-base" / "result.txt"
    second = normalize(root)

    assert first["moved_count"] == 1
    assert target.read_text(encoding="utf-8") == "pass\n"
    assert first["moved"][0]["source"] == "output/pytest-base"
    assert first["moved"][0]["destination"] == "output/_verification/pytest/pytest-base"
    assert second["moved_count"] == 0
    assert (root / "projects" / "huashu-cup" / "2026" / "paper" / "keep.tex").exists()
    manifests = list((root / "output" / "_archive").glob("layout-migration-*/manifest.json"))
    assert len(manifests) == 2


def test_verify_keeps_precontest_projects_isolated(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    report = verify(root)
    assert report["passed"] is True
    assert not (root / "projects" / "huashu-cup" / "2026" / "state" / "decision_log.json").exists()
    assert not (root / "projects" / "huashu-cup" / "2026" / "paper" / "figure_contracts.yaml").exists()


def test_workspace_path_guard_rejects_escape(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    assert inside(root, root / "output" / "_verification")
    assert not inside(root, root.parent / "outside")


def test_power_shell_entrypoint_declares_safe_actions() -> None:
    script = (Path(__file__).resolve().parents[1] / "scripts" / "workspace.ps1").read_text(encoding="utf-8")
    assert "inspect'" in script
    assert "preview'" in script
    assert "normalize'" in script
    assert "verify'" in script
