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
VISUAL_PLAYBOOK = "references/competition-knowledge/playbooks/visual-evidence-quality.md"
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
