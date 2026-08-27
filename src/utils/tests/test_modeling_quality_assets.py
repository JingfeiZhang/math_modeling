from __future__ import annotations

import ast
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
QUALITY_PLAYBOOKS = {
    "references/competition-knowledge/playbooks/data-and-feature-quality.md",
    "references/competition-knowledge/playbooks/algorithm-routing-quality.md",
    "references/competition-knowledge/playbooks/experiment-design-quality.md",
}
CURATED_PLAYBOOKS = {
    "references/competition-knowledge/playbooks/constraint-modeling-quality.md",
    "references/competition-knowledge/playbooks/data-to-decision-modeling.md",
    "references/competition-knowledge/playbooks/contest-paper-reviewer-perspective.md",
    "references/competition-knowledge/playbooks/rehearsal-and-contest-control.md",
}
CURATION_SOURCE_NOTE = "references/competition-knowledge/source-notes/training-materials-curation.md"
VISUAL_PLAYBOOK = "references/competition-knowledge/playbooks/visual-evidence-quality.md"
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


def test_quality_playbooks_are_wired_into_prompt_policy() -> None:
    policy = _load_yaml(ROOT / "config" / "prompt_policy.yaml")
    roles = policy["roles"]

    solver_scope = set(roles["solver"]["read_scope"])
    assert QUALITY_PLAYBOOKS <= solver_scope

    visualization_scope = set(roles["visualization"]["read_scope"])
    assert VISUAL_PLAYBOOK in visualization_scope
    assert "templates/figures/recipe_catalog.yaml" in visualization_scope

    paper_scope = set(roles["paper"]["read_scope"])
    reviewer_scope = set(roles["reviewer"]["read_scope"])
    assert VISUAL_PLAYBOOK in paper_scope
    assert QUALITY_PLAYBOOKS | {VISUAL_PLAYBOOK} <= reviewer_scope

    for relative in QUALITY_PLAYBOOKS | {VISUAL_PLAYBOOK}:
        assert (ROOT / relative).is_file(), relative


def test_curated_training_playbooks_are_indexed_and_non_evidence() -> None:
    knowledge_index = (ROOT / "references/competition-knowledge/index.md").read_text(encoding="utf-8")
    playbook_index = (ROOT / "references/competition-knowledge/playbooks/index.md").read_text(encoding="utf-8")
    source_note = ROOT / CURATION_SOURCE_NOTE

    assert source_note.is_file()
    source_text = source_note.read_text(encoding="utf-8")
    assert "不是 2026 官方规则" in source_text
    assert "不是标准答案" in source_text

    for relative in CURATED_PLAYBOOKS:
        path = ROOT / relative
        assert path.is_file(), relative
        name = path.name
        assert name in knowledge_index
        assert name in playbook_index

        meta = _load_frontmatter(path)
        assert meta["contest_evidence_eligible"] is False
        assert meta["forbidden_use"]
        assert "formal_evidence" in meta["forbidden_use"]
        assert "claim_support" in meta["forbidden_use"]
        assert meta["stage_scope"]
        assert meta["tags"]


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
    visual_playbook = (ROOT / VISUAL_PLAYBOOK).read_text(encoding="utf-8")
    multipanel = ROOT / "templates/figures/python/plot_multipanel_main_result.py"

    assert helper.is_file()
    assert source_note.is_file()
    ast.parse(helper.read_text(encoding="utf-8"), filename=str(helper))
    ast.parse(multipanel.read_text(encoding="utf-8"), filename=str(multipanel))

    assert "publication_helpers.new_panel_figure()" in visual_playbook
    assert "config/figure_style.yaml" in visual_playbook
    assert "figures4papers-integration.md" in visual_playbook

    multipanel_text = multipanel.read_text(encoding="utf-8")
    assert "allow_multiple_primary_axes=True" in multipanel_text
    assert "shared_legend" in multipanel_text

    source_text = source_note.read_text(encoding="utf-8")
    assert "config/figure_style.yaml" in source_text
    assert "明确不吸收" in source_text
