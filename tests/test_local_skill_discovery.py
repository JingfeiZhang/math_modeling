from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
LOCAL_SKILLS = ("visualization-design", "literature-guided-modeling")


def load_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    _, raw, _ = text.split("---", 2)
    payload = yaml.safe_load(raw)
    assert isinstance(payload, dict)
    return payload


def test_project_skill_entries_resolve_to_one_canonical_source() -> None:
    for name in LOCAL_SKILLS:
        entry = ROOT / ".agents" / "skills" / name / "SKILL.md"
        frontmatter = load_frontmatter(entry)
        assert frontmatter["name"] == name
        canonical_value = frontmatter["metadata"]["canonical_skill"]
        canonical = (entry.parent / canonical_value).resolve()
        assert canonical == (ROOT / "skill_staging" / name / "SKILL.md").resolve()
        assert canonical.is_file()
        assert load_frontmatter(canonical)["name"] == name


def test_project_skill_entries_are_discovery_shims_not_policy_copies() -> None:
    for name in LOCAL_SKILLS:
        entry = ROOT / ".agents" / "skills" / name / "SKILL.md"
        body = entry.read_text(encoding="utf-8")
        assert len(body) < 1200
        assert "prompt_policy.yaml" not in body
        assert "blocking" not in body
        assert "warning" not in body


def test_canonical_local_skills_consume_assembled_packets() -> None:
    for name in LOCAL_SKILLS:
        skill_root = ROOT / "skill_staging" / name
        instructions = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        metadata = yaml.safe_load((skill_root / "agents" / "openai.yaml").read_text(encoding="utf-8"))
        assert "prompt_policy.yaml" not in instructions
        assert "prompt_policy.yaml" not in metadata["interface"]["default_prompt"]
        assert "current assembled" in metadata["interface"]["default_prompt"]


def test_visualization_validator_discovers_workspace_and_isolated_project(tmp_path: Path) -> None:
    script = ROOT / "skill_staging" / "visualization-design" / "scripts" / "validate_handoff.py"
    spec = importlib.util.spec_from_file_location("visualization_handoff_validator", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    workspace = tmp_path / "workspace"
    schemas = workspace / "config" / "schemas"
    schemas.mkdir(parents=True)
    (workspace / "config" / "projects.json").write_text("{}\n", encoding="utf-8")
    for name in module.WORKSPACE_SCHEMA_FILES:
        (schemas / name).write_text("{}\n", encoding="utf-8")
    project = workspace / "projects" / "cumcm" / "2026"
    project.mkdir(parents=True)
    (project / "project.yaml").write_text("project_id: cumcm-2026\n", encoding="utf-8")
    manifest = project / "experiments" / "C" / "Q1" / "formal" / "run-1" / "figure_data_manifest.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}\n", encoding="utf-8")

    assert module.discover_workspace_root(None, manifest) == workspace.resolve()
    assert module.discover_project_root(workspace, manifest) == project.resolve()
