from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from src.workflow.competition_workflow import initialize, preflight, resolve_run_config, status
from src.workflow.project_workspace import (
    contest_payload,
    list_projects,
    preflight as project_preflight,
    registered_projects,
    resolve_project,
    scaffold,
)


ROOT = Path(__file__).resolve().parents[1]


def prepare_hub(tmp_path: Path) -> Path:
    hub = tmp_path / "hub"
    (hub / "config").mkdir(parents=True)
    shutil.copy2(ROOT / "config" / "competition_profiles.yaml", hub / "config" / "competition_profiles.yaml")
    shutil.copy2(ROOT / "config" / "projects.json", hub / "config" / "projects.json")
    for relative in (
        "config/workflow.yaml",
        "config/figure_style.yaml",
        "skills.lock.yaml",
        "environment.yml",
        "templates/figures/figure_contract_v2.schema.json",
        "templates/figures/figure_contract_v2.template.yaml",
    ):
        source = ROOT / relative
        target = hub / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return hub


def test_scaffolded_projects_are_precontest_and_isolated(tmp_path: Path) -> None:
    hub = prepare_hub(tmp_path)
    huashu = scaffold(hub, "huashu-cup-2026")
    cumcm = scaffold(hub, "cumcm-2026")

    assert huashu["problem"] == "TBD"
    assert cumcm["problem"] == "TBD"
    assert huashu["root"] != cumcm["root"]
    for project_id in ("huashu-cup-2026", "cumcm-2026"):
        check = project_preflight(hub, project_id)
        assert check["passed"] is True
        project_root = hub / check["root"]
        assert not (project_root / "state" / "decision_log.json").exists()
        assert not (project_root / "paper" / "figure_contracts.yaml").exists()

    listing = list_projects(hub)
    assert {item["project_id"] for item in listing["projects"]} == {"huashu-cup-2026", "cumcm-2026"}
    assert listing["default_project"] is None


def test_huashu_inherits_cumcm_defaults_but_remains_overridable(tmp_path: Path) -> None:
    hub = prepare_hub(tmp_path)
    project = resolve_project(hub, "huashu-cup-2026")
    payload = contest_payload(hub, project)

    assert payload["competition"] == "HUASHU_CUP"
    assert payload["rules"]["status"] == "inherited_cumcm_default"
    assert payload["format"]["paper_body_max_pages"] == 30
    assert payload["format"]["provisional"] is True
    assert payload["paper"]["template_family"] == "cumcm-2026"

    project["overrides"] = {"format": {"paper_body_max_pages": 24}, "deadline": "2026-08-08T18:00:00+08:00"}
    overridden = contest_payload(hub, project)
    assert overridden["format"]["paper_body_max_pages"] == 24
    assert overridden["format"]["paper_max_mb"] == 20
    assert overridden["deadline"] == "2026-08-08T18:00:00+08:00"


def test_initializing_one_project_does_not_create_state_in_another(tmp_path: Path) -> None:
    hub = prepare_hub(tmp_path)
    huashu_status = scaffold(hub, "huashu-cup-2026")
    cumcm_status = scaffold(hub, "cumcm-2026")
    huashu_root = hub / huashu_status["root"]
    cumcm_root = hub / cumcm_status["root"]
    problem_file = huashu_root / "problems" / "incoming" / "problem-A.txt"
    problem_file.parent.mkdir(parents=True, exist_ok=True)
    problem_file.write_text("Q1 build a prediction model.\nQ2 optimize the resulting plan.\n", encoding="utf-8")

    result = initialize(huashu_root, "A", problem_file, ROOT)

    assert result["questions"] == ["Q1", "Q2"]
    assert (huashu_root / "state" / "decision_log.json").is_file()
    assert (huashu_root / "paper" / "figure_contracts.yaml").is_file()
    assert (huashu_root / "paper" / "main.tex").is_file()
    assert status(huashu_root)["phase"] == "ACTIVE"
    assert status(cumcm_root)["phase"] == "PRECONTEST"
    assert not (cumcm_root / "state" / "decision_log.json").exists()
    assert not (cumcm_root / "paper" / "figure_contracts.yaml").exists()
    assert preflight(huashu_root, ROOT)["passed"] is True


def test_registry_rejects_project_root_escape_and_duplicates(tmp_path: Path) -> None:
    hub = prepare_hub(tmp_path)
    registry_path = hub / "config" / "projects.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["projects"][0]["root"] = "../outside"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(ValueError, match="under projects"):
        registered_projects(hub)

    shutil.copy2(ROOT / "config" / "projects.json", registry_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["projects"][1]["root"] = registry["projects"][0]["root"]
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        registered_projects(hub)


def test_powershell_entrypoints_require_explicit_project_routing() -> None:
    workflow = (ROOT / "scripts" / "workflow.ps1").read_text(encoding="utf-8")
    assert "[string]$Project" in workflow
    assert "Resolve-ModelingProject -Project $Project" in workflow
    assert "-ProjectRoot $root -WorkspaceRoot $hub" in workflow
    assert (ROOT / "scripts" / "project.ps1").is_file()
    registry = json.loads((ROOT / "config" / "projects.json").read_text(encoding="utf-8"))
    assert registry["default_project"] is None


def _write_run_fixture(tmp_path: Path, *, runner: str = "src/runner.py", inputs: list[str] | None = None, output_root: str = "experiments/C/Q1") -> Path:
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)
    (project_root / "data").mkdir()
    (project_root / "src" / "runner.py").write_text("print('ok')\n", encoding="utf-8")
    (project_root / "data" / "input.csv").write_text("x\n1\n", encoding="utf-8")
    config_path = project_root / "experiment.yaml"
    config = {
        "experiment_id": "run-001",
        "problem": "C",
        "question": "Q1",
        "engine": "python",
        "runner": runner,
        "seed": 7,
        "output_root": output_root,
        "methods": ["main"],
        "metrics": ["rmse"],
        "inputs": inputs or ["data/input.csv"],
    }
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return config_path


def test_run_config_rejects_runner_path_escape(tmp_path: Path) -> None:
    config_path = _write_run_fixture(tmp_path, runner="../outside.py")
    (tmp_path / "outside.py").write_text("print('outside')\n", encoding="utf-8")
    with pytest.raises(ValueError, match="runner path escapes workspace"):
        resolve_run_config(config_path.parent, config_path)


def test_run_config_rejects_input_path_escape(tmp_path: Path) -> None:
    config_path = _write_run_fixture(tmp_path, inputs=["../outside.csv"])
    (tmp_path / "outside.csv").write_text("x\n2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="input path escapes workspace"):
        resolve_run_config(config_path.parent, config_path)


def test_run_config_rejects_output_path_escape(tmp_path: Path) -> None:
    config_path = _write_run_fixture(tmp_path, output_root="../outside-results")
    with pytest.raises(ValueError, match="output-root path escapes workspace"):
        resolve_run_config(config_path.parent, config_path)


def test_run_config_accepts_project_local_paths(tmp_path: Path) -> None:
    config_path = _write_run_fixture(tmp_path)
    resolved = resolve_run_config(config_path.parent, config_path)
    assert resolved["runner_path"] == "src/runner.py"
    assert resolved["experiment_root"] == "experiments/C/Q1/run-001"
