from __future__ import annotations

import ast
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
QUALITY_GUIDES = {
    "references/competition-knowledge/guides/academic-quality-standard.md",
    "references/competition-knowledge/guides/award-oriented-modeling.md",
    "references/competition-knowledge/guides/data-and-feature-quality.md",
    "references/competition-knowledge/guides/algorithm-routing-quality.md",
    "references/competition-knowledge/guides/experiment-design-quality.md",
    "references/competition-knowledge/guides/visual-evidence-quality.md",
}
CROSS_STAGE_GUIDES = {
    "references/competition-knowledge/guides/contest-paper-reviewer-perspective.md",
    "references/competition-knowledge/guides/rehearsal-and-contest-control.md",
}
ROUTABLE_PLAYBOOKS = {
    "references/competition-knowledge/playbooks/constraint-modeling-quality.md",
    "references/competition-knowledge/playbooks/data-to-decision-modeling.md",
    "references/competition-knowledge/playbooks/predict-then-optimize.md",
    "references/competition-knowledge/playbooks/resource-allocation-under-uncertainty.md",
    "references/competition-knowledge/playbooks/mechanism-fit-and-scenario.md",
}
LEGACY_NONROUTABLE_PLAYBOOKS = {
    "academic-quality-standard.md",
    "award-oriented-modeling.md",
    "data-and-feature-quality.md",
    "algorithm-routing-quality.md",
    "experiment-design-quality.md",
    "visual-evidence-quality.md",
}
CURATION_SOURCE_NOTE = "references/competition-knowledge/source-notes/training-materials-curation.md"
VISUAL_GUIDE = "references/competition-knowledge/guides/visual-evidence-quality.md"
REFERENCE_LIBRARY_ADAPTER = "src/workflow/reference_library_cli.py"
RENDERING_HELPER = "templates/figures/python/publication_helpers.py"
FIGURE_SOURCE_NOTE = "references/figure-sources/figures4papers-integration.md"
NEW_RECIPES = {
    "observed-vs-predicted",
    "error-by-group",
    "distribution-ecdf",
    "rank-stability",
    "schedule-gantt",
    "resource-profile",
}
PLAYBOOK_REQUIRED_SECTIONS = {
    "触发与排除",
    "输入输出合同",
    "分阶段行动",
    "baseline 与升级",
    "联合诊断",
    "停止与回退",
    "Candidate 交接",
    "禁止事项",
}
PLAYBOOK_ALLOWED_STAGES = {"P1", "P2", "P3a", "P3b"}
PLAYBOOK_ALLOWED_USE = {
    "model_direction",
    "assumption_check",
    "baseline_design",
    "risk_probe",
}
PLAYBOOK_FORBIDDEN_USE = {
    "academic_citation",
    "formal_evidence",
    "claim_support",
    "figure_contract",
    "submission",
}


def _load_yaml(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"Missing YAML frontmatter: {path}"
    _, frontmatter, _ = text.split("---", 2)
    payload = yaml.safe_load(frontmatter)
    assert isinstance(payload, dict)
    return payload


def _adapter_routable_filenames() -> set[str]:
    adapter = ROOT / REFERENCE_LIBRARY_ADAPTER
    tree = ast.parse(adapter.read_text(encoding="utf-8"), filename=str(adapter))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "ROUTABLE_PLAYBOOK_FILENAMES" for target in node.targets):
            continue
        value = ast.literal_eval(node.value)
        return {str(item) for item in value}
    raise AssertionError("ROUTABLE_PLAYBOOK_FILENAMES is missing from reference_library_cli.py")


def test_quality_guides_are_wired_into_prompt_policy() -> None:
    policy = _load_yaml(ROOT / "config" / "prompt_policy.yaml")
    roles = policy["roles"]

    assert policy["academic_quality"]["profile"] == (
        "references/competition-knowledge/guides/academic-quality-standard.md"
    )

    solver_scope = set(roles["solver"]["read_scope"])
    expected_solver_guides = {
        "references/competition-knowledge/guides/academic-quality-standard.md",
        "references/competition-knowledge/guides/award-oriented-modeling.md",
        "references/competition-knowledge/guides/data-and-feature-quality.md",
        "references/competition-knowledge/guides/algorithm-routing-quality.md",
        "references/competition-knowledge/guides/experiment-design-quality.md",
    }
    assert expected_solver_guides <= solver_scope

    visualization_scope = set(roles["visualization"]["read_scope"])
    assert VISUAL_GUIDE in visualization_scope
    assert "templates/figures/recipe_catalog.yaml" in visualization_scope

    paper_scope = set(roles["paper"]["read_scope"])
    reviewer_scope = set(roles["reviewer"]["read_scope"])
    assert VISUAL_GUIDE in paper_scope
    assert QUALITY_GUIDES <= reviewer_scope | expected_solver_guides

    for relative in QUALITY_GUIDES | CROSS_STAGE_GUIDES:
        assert (ROOT / relative).is_file(), relative

    policy_text = (ROOT / "config/prompt_policy.yaml").read_text(encoding="utf-8")
    for relative in QUALITY_GUIDES:
        old = relative.replace("/guides/", "/playbooks/")
        assert old not in policy_text, f"stale quality-guide path remains: {old}"


def test_reference_library_runtime_boundary_is_strict_l3_only() -> None:
    adapter = ROOT / REFERENCE_LIBRARY_ADAPTER
    script = (ROOT / "scripts/reference-library.ps1").read_text(encoding="utf-8")
    assert adapter.is_file()
    ast.parse(adapter.read_text(encoding="utf-8"), filename=str(adapter))
    assert "reference_library_cli.py" in script

    expected_names = {Path(relative).name for relative in ROUTABLE_PLAYBOOKS}
    assert _adapter_routable_filenames() == expected_names
    assert not (_adapter_routable_filenames() & LEGACY_NONROUTABLE_PLAYBOOKS)

    for relative in sorted(ROUTABLE_PLAYBOOKS):
        path = ROOT / relative
        meta = _load_frontmatter(path)
        text = path.read_text(encoding="utf-8")

        assert meta["playbook_version"] == 1
        assert set(meta["stage_scope"]) <= PLAYBOOK_ALLOWED_STAGES
        assert meta["stage_scope"]
        assert meta["evidence_status"] == "P1-P3-non-evidence"
        assert meta["contest_evidence_eligible"] is False
        assert set(meta["allowed_use"]) == PLAYBOOK_ALLOWED_USE
        assert PLAYBOOK_FORBIDDEN_USE <= set(meta["forbidden_use"])
        assert meta["modules"]
        assert meta["tags"]

        for section in PLAYBOOK_REQUIRED_SECTIONS:
            assert f"## {section}" in text, f"{relative} missing L3 section: {section}"


def test_curated_training_assets_preserve_reference_library_boundaries() -> None:
    knowledge_index = (ROOT / "references/competition-knowledge/index.md").read_text(encoding="utf-8")
    playbook_index = (ROOT / "references/competition-knowledge/playbooks/index.md").read_text(encoding="utf-8")
    guides_index = (ROOT / "references/competition-knowledge/guides/index.md").read_text(encoding="utf-8")
    source_note = ROOT / CURATION_SOURCE_NOTE

    assert source_note.is_file()
    source_text = source_note.read_text(encoding="utf-8")
    assert "不是 2026 官方规则" in source_text
    assert "不是标准答案" in source_text
    assert "playbook 与 guide" in source_text

    for relative in ROUTABLE_PLAYBOOKS:
        path = ROOT / relative
        assert path.name in knowledge_index
        assert path.name in playbook_index

    for relative in QUALITY_GUIDES | CROSS_STAGE_GUIDES:
        path = ROOT / relative
        assert path.name in knowledge_index or path.name in guides_index
        assert path.name in guides_index
        assert relative not in ROUTABLE_PLAYBOOKS

    assert "reference-library 可自动路由" in playbook_index
    assert "不会被 `reference_library.py` 当成 L3 Playbook 自动路由" in guides_index


def test_figure_recipe_catalog_points_to_existing_parseable_scripts() -> None:
    catalog = _load_yaml(ROOT / "templates" / "figures" / "recipe_catalog.yaml")
    recipes = catalog["recipes"]
    by_id = {entry["id"]: entry for entry in recipes}
    assert NEW_RECIPES <= set(by_id)

    for entry in recipes + catalog.get("compatibility_recipes", []):
        script = ROOT / "templates" / "figures" / entry["script"]
        assert script.is_file(), f"Missing recipe script: {entry['id']} -> {script}"
        if script.suffix == ".py":
            ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        assert entry["required_columns"], f"Recipe has no evidence-column contract: {entry['id']}"


def test_publication_rendering_patterns_remain_internal_and_parseable() -> None:
    helper = ROOT / RENDERING_HELPER
    source_note = ROOT / FIGURE_SOURCE_NOTE
    visual_guide = (ROOT / VISUAL_GUIDE).read_text(encoding="utf-8")
    multipanel = ROOT / "templates/figures/python/plot_multipanel_main_result.py"

    assert helper.is_file()
    assert source_note.is_file()
    ast.parse(helper.read_text(encoding="utf-8"), filename=str(helper))
    ast.parse(multipanel.read_text(encoding="utf-8"), filename=str(multipanel))

    assert "publication_helpers.new_panel_figure()" in visual_guide
    assert "config/figure_style.yaml" in visual_guide
    assert "figures4papers-integration.md" in visual_guide

    multipanel_text = multipanel.read_text(encoding="utf-8")
    assert "allow_multiple_primary_axes=True" in multipanel_text
    assert "shared_legend" in multipanel_text

    source_text = source_note.read_text(encoding="utf-8")
    assert "config/figure_style.yaml" in source_text
    assert "明确不吸收" in source_text
